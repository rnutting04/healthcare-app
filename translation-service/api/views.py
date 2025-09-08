import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.serializers import TranslationRequest, JobResponse, Result, JobOrResult
from services.translation import get_translation_cache_key, RESULTS_CACHE_PREFIX, REQUEST_QUEUE_KEY
from auth import verify_token
from db import redis_client

router = APIRouter()
logger = logging.getLogger(__name__)

#--- API Endpoints ---

@router.get('/health', tags=['Monitoring'])
#checks the status of the service and its connection to Redis
async def health_check():
    if redis_client and redis_client.ping():
        return {"api_status": "ok", "redis_status": "ok"}
    raise HTTPException(status_code=503, detail="Service Unavailable: Cannot connect to Redis.")

#defines the endpoint for submitting a new translation job
@router.post(
    '/translate', 
    response_model=JobOrResult,
    status_code=status.HTTP_200_OK,
    tags=['Translation'],
    dependencies=[Depends(verify_token)]
)
#accepts a translation request, checks the cache, or queues it for a background worker
async def submit_translation(translation_request: TranslationRequest, response: Response):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Service Unavailable: Cannot Connect to Redis.")

    # --- Cache Check ---
    #generate the unique key for this specific text and language combination.
    cache_key = get_translation_cache_key(translation_request.text, translation_request.target_language)
    truncated_key = cache_key.split(':')[-1][:12]
    in_progress_payload = json.dumps({'status': 'in_progress', 'result': None})

    #atomic operation: attempt to set the key if it does not exist
    was_set = redis_client.set(cache_key, in_progress_payload, ex=600, nx=True)

    # --- Cache Miss and New Job ---
    if was_set:
        logger.info(f"Cache miss for key ending in: ...{truncated_key}. Submitting new job.")
        logger.info("job accepted")
        #generate a new, unique ID for this job request
        request_id = str(uuid.uuid4())

        #dictionary containing all the information the worker needs to process the job
        task = {
            'id': request_id,
            'text': translation_request.text,
            'lang': translation_request.target_language,
        }

        #push job to the end of the worker queue in Redis
        redis_client.rpush(REQUEST_QUEUE_KEY, json.dumps(task))
        response.status_code = status.HTTP_202_ACCEPTED
        return JobResponse(message="Request accepted.", request_id=request_id)

    # --- CACHE HIT (Job is in_progress or completed) ---
    existing_data = redis_client.get(cache_key)
    data = json.loads(existing_data) # Parse the JSON payload
    if data.get('status') == 'in_progress':
        logger.info(f"Job rejected.")
    else:
        logger.info(f"Cache hit for completed job for key ending in: ... {truncated_key}")
    return Result(
        status=data.get('status'),
        result=data.get('result'),
        from_cache=True
    )

@router.get(
    "/result/{request_id}", 
    response_model=Result,
    tags=['Translation'],
    dependencies=[Depends(verify_token)]
)
#retrieves the result of a translation job by its ID
async def get_translation_result(request_id: str):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Service Unavailable: Cannot connect to Redis.")

    #key where the result should be stored
    result_key = f"{RESULTS_CACHE_PREFIX}{request_id}"
    # Try to get the result data from Redis.
    result_json = redis_client.get(result_key)
    if not result_json:
        #the ID is invalid or the result has expired
        raise HTTPException(status_code=404, detail="Request ID not found.")

    #if data was found, parse the JSON string back into a Python dictionary
    result = json.loads(result_json)
    if result.get('status') in ['completed', 'failed']:
        redis_client.expire(result_key, 300)

    return Result(**result)
