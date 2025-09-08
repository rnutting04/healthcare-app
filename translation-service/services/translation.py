import os
import json
import time
import hashlib
import logging
import uuid
from threading import Lock
from transformers import pipeline
from asgiref.sync import async_to_sync
from channels_redis.core import RedisChannelLayer

from translation_service.config import (
    LANGUAGE_CODES, HELSINKI_NAME_TEMPLATE, BATCH_SIZE, BATCH_TIMEOUT,
    TRANSLATION_CACHE_PREFIX, RESULTS_CACHE_PREFIX, REQUEST_QUEUE_KEY
)

logger = logging.getLogger(__name__)

# --- Manual Channel Layer Configuration ---
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('TRANSLATION_REDIS_DB', '3'))

channel_layer = RedisChannelLayer(hosts=[f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"])

# --- In-Memory Caching for ML Models ---
#store the loaded models to avoid reloading them on every request
model_cache = {}
#prevent race conditions where two threads might try to load the same model simultaneously
model_cache_lock = Lock()

def on_translation_complete(request_id, translated_text, status):
    """
    This function is called by your translation worker when a job is done.
    """
    try:
        logger.info(f"--- TRANSLATION WORKER: Publishing update for request_id: {request_id} ---")
        group_name = f"translation_{request_id}"
        
        if status == 'completed':
            message_type = "translation.complete"
            payload = {
                "job_id": request_id,
                "result": translated_text,
            }
        else: # e.g., 'failed'
            message_type = "translation.error"
            payload = {
                "job_id": request_id,
                "message": translated_text, # The error message
            }

        message = {
            "type": message_type,
            **payload
        }
        # Send the message to the Redis group
        async_to_sync(channel_layer.group_send)(group_name, message)
    except Exception as e:
        logger.error(f"failed to publish update for request: {e}")

#generates a consistent, unique cache key for a translated text string
def get_translation_cache_key(text: str, lang: str):
    key_string = f"{text}:{lang}".encode('utf-8')
    key_hash = hashlib.sha256(key_string).hexdigest()
    return f"{TRANSLATION_CACHE_PREFIX}{key_hash}"

#loads a specific translation model from Hugging Face
#if the model is already loaded, it returns the cached instance
def get_translation_pipeline(target_lang_code: str):
    if target_lang_code not in LANGUAGE_CODES:
        return None, f"Language code: '{target_lang_code}' not supported."

    model_name = HELSINKI_NAME_TEMPLATE.format(lang_code=target_lang_code)
    
    #use a lock to ensure thread-safe access to the model_cache dictionary
    with model_cache_lock:
        #if the model is already in our cache, return it
        if model_name in model_cache:
            return model_cache[model_name], None
        
        logger.info(f"Loading model: {model_name}...")
        try:
            #download and initialize the translation pipeline from Hugging Face
            translator = pipeline('translation', model=model_name)
            model_cache[model_name] = translator
            logger.info(f"Model {model_name} loaded and cached.")
            return translator, None
        except Exception as e:
            error_message = f"Failed to load model {model_name}: {e}"
            logger.error(error_message)
            return None, error_message

#runs continuously in a background thread to process jobs
#fetches jobs from the Redis queue and processes them in batches
def translation_worker(redis_client):
    if not redis_client: return

    while True:
        jobs_to_process = []
        try:
            #loop attempts to pull a batch of jobs from the queue
            for _ in range(BATCH_SIZE):
                #blpop is a "blocking pop". It waits for an item to appear or until the timeout
                #this is highly efficient as it doesn't constantly poll Redis
                task_json_tuple = redis_client.blpop(REQUEST_QUEUE_KEY, timeout=int(BATCH_TIMEOUT))

                #timeout reached, process the jobs we have so far
                if not task_json_tuple:
                    break

                #the item from Redis is a JSON string, so we parse it into a Python dict
                jobs_to_process.append(json.loads(task_json_tuple[1]))
        except Exception as e:
            logger.error(f"Error popping job from Redis: {e}")
            time.sleep(BATCH_TIMEOUT)
            continue

        #if no jobs were fetched, loop again to wait for more.
        if not jobs_to_process:
            continue

        logger.info(f"Processing a batch of {len(jobs_to_process)} jobs.")
        #group jobs by target language so we can process them with the same model
        grouped_by_lang = {}
        for job in jobs_to_process:
            lang = job['lang']
            grouped_by_lang.setdefault(lang, []).append(job)

        #process each language group as a separate batch.
        for lang, jobs in grouped_by_lang.items():
            translator_pipeline, error = get_translation_pipeline(lang)

            #if model failed to load, mark all jobs for this language as failed
            if not translator_pipeline:
                for job in jobs:
                    job['status'] = 'failed'
                    job['result'] = error
                continue

            try:
                #create a list of just the texts to be translated
                texts = [job['text'] for job in jobs]

                #pass the entire list to the pipeline for efficient, batched translation
                translated_results = translator_pipeline(texts)

                #map the results back to their original jobs
                for i, job in enumerate(jobs):
                    job['status'] = 'completed'
                    job['result'] = translated_results[i]['translation_text']
            except Exception as e:
                logger.error(f"Error during batch translation for language {lang}: {e}")
                for job in jobs:
                    job['status'] = 'failed'
                    job['result'] = "Error during batch processing."
        
        # --- Save all results back to Redis ---
        try:
            #use a Redis pipeline to execute multiple commands in a single network round-trip for efficiency
            with redis_client.pipeline() as pipe:
                for job in jobs_to_process:
                    on_translation_complete(
                        request_id=job['id'], 
                        translated_text=job['result'], 
                        status=job['status']
                    )
                    cache_key = get_translation_cache_key(job['text'], job['lang'])

                    #create the final payload.
                    final_payload = json.dumps({
                        'status': job['status'],
                        'result': job['result']
                    })

                    #overwrite the 'in_progress' status with the final result
                    #set a long expiry (e.g., 1 hour) for the completed translation
                    pipe.set(cache_key, final_payload, ex=3600)

                    #store the final job status and result for user pickup
                    result_key = f"{RESULTS_CACHE_PREFIX}{job['id']}"
                    pipe.set(result_key, final_payload, ex=300) # result available for 5 mins

                pipe.execute()
            logger.info(f"Successfully saved results for {len(jobs_to_process)} jobs to Redis.")
        except Exception as e:
            logger.error(f"Error saving results to Redis: {e}")
