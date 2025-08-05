import os
import json
import logging
import redis
import asyncio
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# LangChain imports
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from langchain.schema import Document
from langchain_community.docstore.document import Document as LangchainDocument

logger = logging.getLogger(__name__)


class RedisQueueManager:
    """Manages job queue using Redis"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self.queue_key = "rag:embedding:queue"
        self.processing_key = "rag:embedding:processing"
        self.status_key_prefix = "rag:embedding:status:"
        self.lock_key = "rag:embedding:lock"
        self.worker_thread = None
        self.channel_layer = get_channel_layer()
        self.start_worker()
    
    def start_worker(self):
        """Start background worker thread"""
        if not self.worker_thread or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
            logger.info("Started embedding queue worker thread")
    
    def add_job(self, job_data: Dict[str, Any]) -> str:
        """Add job to queue"""
        job_id = job_data['job_id']
        
        # Store job data
        self.redis_client.setex(
            f"{self.status_key_prefix}{job_id}",
            settings.RAG_PROCESSING_TIMEOUT * 2,  # TTL
            json.dumps({
                **job_data,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            })
        )
        
        # Add to queue
        self.redis_client.rpush(self.queue_key, job_id)
        logger.info(f"Added job {job_id} to embedding queue")
        
        return job_id
    
    def _process_queue(self):
        """Background worker to process queue"""
        while True:
            try:
                # Check for jobs
                job_id = self.redis_client.blpop(self.queue_key, timeout=5)
                
                if job_id:
                    job_id = job_id[1]  # blpop returns (key, value)
                    
                    # Check concurrent processing limit
                    processing_count = self.redis_client.scard(self.processing_key)
                    if processing_count >= settings.RAG_MAX_CONCURRENT_PROCESSING:
                        # Put back in queue and wait
                        self.redis_client.lpush(self.queue_key, job_id)
                        time.sleep(5)
                        continue
                    
                    # Get job data
                    job_data = self.redis_client.get(f"{self.status_key_prefix}{job_id}")
                    if not job_data:
                        logger.error(f"Job {job_id} data not found")
                        continue
                    
                    job_data = json.loads(job_data)
                    
                    # Mark as processing
                    self.redis_client.sadd(self.processing_key, job_id)
                    self._update_job_status(job_id, 'processing', 'Starting document processing')
                    
                    # Process the job
                    try:
                        self._process_job(job_data)
                        self._update_job_status(job_id, 'completed', 'Document processed successfully')
                    except Exception as e:
                        logger.error(f"Error processing job {job_id}: {str(e)}")
                        self._handle_job_failure(job_id, job_data, str(e))
                    finally:
                        # Remove from processing set
                        self.redis_client.srem(self.processing_key, job_id)
                
            except Exception as e:
                logger.error(f"Queue worker error: {str(e)}")
                time.sleep(5)
    
    def _process_job(self, job_data: Dict[str, Any]):
        """Process a single embedding job"""
        job_id = job_data['job_id']
        document_id = job_data['document_id']
        cancer_type_id = job_data['cancer_type_id']
        jwt_token = job_data['jwt_token']
        
        logger.info(f"Processing job {job_id} for document {document_id}")
        
        # Download file from file service
        temp_file_path = None
        try:
            headers = {'Authorization': f'Bearer {jwt_token}'}
            response = requests.get(
                f"{settings.FILE_SERVICE_URL}/api/files/{document_id}",
                headers=headers,
                stream=True
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to download file: {response.status_code}")
            
            # Save to temp file
            temp_file_path = os.path.join(settings.TEMP_FILE_PATH, f"{document_id}.pdf")
            with open(temp_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Process document with LangChain
            self._update_job_status(job_id, 'processing', 'Loading document', {
                'phase': 'loading',
                'total_chunks': 0,
                'processed_chunks': 0,
                'percentage': 0
            })
            loader = PyPDFLoader(temp_file_path)
            documents = loader.load()
            
            # Split documents
            self._update_job_status(job_id, 'processing', 'Splitting document into chunks', {
                'phase': 'splitting',
                'total_chunks': 0,
                'processed_chunks': 0,
                'percentage': 10
            })
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.RAG_CHUNK_SIZE,
                chunk_overlap=settings.RAG_CHUNK_OVERLAP,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = text_splitter.split_documents(documents)
            
            # Generate embeddings
            self._update_job_status(job_id, 'processing', f'Generating embeddings for {len(chunks)} chunks', {
                'phase': 'embedding',
                'total_chunks': len(chunks),
                'processed_chunks': 0,
                'percentage': 20
            })
            embeddings_model = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_EMBEDDING_MODEL
            )
            
            # Prepare chunks for database
            chunk_data = []
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = embeddings_model.embed_query(chunk.page_content)
                
                chunk_data.append({
                    'document_id': document_id,
                    'cancer_type_id': cancer_type_id,
                    'chunk_index': i,
                    'chunk_text': chunk.page_content,
                    'embedding': embedding,
                    'metadata': {
                        'page': chunk.metadata.get('page', 0),
                        'source': chunk.metadata.get('source', ''),
                        'job_id': job_id
                    }
                })
                
                # Update progress - send update for every chunk for real-time feel
                progress_percentage = 20 + int(((i + 1) / len(chunks)) * 60)  # 20-80% for embedding phase
                self._update_job_status(
                    job_id, 
                    'processing', 
                    f'Processing chunk {i + 1} of {len(chunks)}',
                    {
                        'phase': 'embedding',
                        'total_chunks': len(chunks),
                        'processed_chunks': i + 1,
                        'percentage': progress_percentage,
                        'current_chunk': {
                            'index': i + 1,
                            'page': chunk.metadata.get('page', 0),
                            'preview': chunk.page_content[:100] + '...' if len(chunk.page_content) > 100 else chunk.page_content
                        }
                    }
                )
            
            # Save to database via database service
            self._update_job_status(job_id, 'processing', 'Saving embeddings to database', {
                'phase': 'saving',
                'total_chunks': len(chunks),
                'processed_chunks': len(chunks),
                'percentage': 90
            })
            save_response = requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/rag/embeddings/bulk_create/",
                headers={'X-Service-Token': settings.DATABASE_SERVICE_TOKEN},
                json={
                    'document_id': document_id,
                    'chunks': chunk_data
                }
            )
            
            if save_response.status_code != 201:
                raise Exception(f"Failed to save embeddings: {save_response.text}")
            
            logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks")
            
            # Send final completion update
            self._update_job_status(job_id, 'completed', f'Successfully processed {len(chunks)} chunks', {
                'phase': 'completed',
                'total_chunks': len(chunks),
                'processed_chunks': len(chunks),
                'percentage': 100
            })
            
        finally:
            # Cleanup temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def _update_job_status(self, job_id: str, status: str, message: str, progress_data: dict = None):
        """Update job status in Redis and database"""
        # Update Redis
        job_data = self.redis_client.get(f"{self.status_key_prefix}{job_id}")
        if job_data:
            job_data = json.loads(job_data)
            job_data['status'] = status
            job_data['message'] = message
            job_data['updated_at'] = datetime.now().isoformat()
            if progress_data:
                job_data['progress'] = progress_data
            self.redis_client.setex(
                f"{self.status_key_prefix}{job_id}",
                settings.RAG_PROCESSING_TIMEOUT * 2,
                json.dumps(job_data)
            )
        
        # Update database embedding job
        try:
            # Create message with progress data
            if progress_data:
                message_data = {
                    'text': message,
                    'progress': progress_data
                }
                message_json = json.dumps(message_data)
            else:
                message_json = message
            
            update_data = {
                'status': status,
                'message': message_json
            }
            if status == 'completed':
                update_data['completed_at'] = datetime.now().isoformat()
            
            requests.patch(
                f"{settings.DATABASE_SERVICE_URL}/api/rag/embedding-jobs/{job_id}/",
                headers={'X-Service-Token': settings.DATABASE_SERVICE_TOKEN},
                json=update_data
            )
        except Exception as e:
            logger.error(f"Failed to update job status in database: {str(e)}")
        
        # Send WebSocket update
        self._send_websocket_update(job_id, status, message, progress_data)
    
    def _send_websocket_update(self, job_id: str, status: str, message: str, progress_data: dict = None):
        """Send real-time update via WebSocket"""
        try:
            group_name = f'embedding_job_{job_id}'
            
            # Prepare the message
            websocket_data = {
                'type': 'embedding_progress',
                'job_id': job_id,
                'status': status,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            if progress_data:
                websocket_data['progress'] = progress_data
            
            # Send to WebSocket group
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                websocket_data
            )
            
            logger.debug(f"Sent WebSocket update for job {job_id}: {status}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket update: {str(e)}")
    
    def _handle_job_failure(self, job_id: str, job_data: Dict[str, Any], error: str):
        """Handle failed job with retry logic"""
        retry_count = job_data.get('retry_count', 0)
        
        if retry_count < settings.RAG_RETRY_MAX_ATTEMPTS:
            # Retry the job
            job_data['retry_count'] = retry_count + 1
            job_data['last_error'] = error
            
            # Update Redis
            self.redis_client.setex(
                f"{self.status_key_prefix}{job_id}",
                settings.RAG_PROCESSING_TIMEOUT * 2,
                json.dumps(job_data)
            )
            
            # Add back to queue with delay
            time.sleep(settings.RAG_RETRY_DELAY)
            self.redis_client.rpush(self.queue_key, job_id)
            
            # Update database with retry count
            try:
                requests.patch(
                    f"{settings.DATABASE_SERVICE_URL}/api/rag/embedding-jobs/{job_id}/",
                    headers={'X-Service-Token': settings.DATABASE_SERVICE_TOKEN},
                    json={
                        'status': 'retrying',
                        'message': f'Retry attempt {retry_count + 1} of {settings.RAG_RETRY_MAX_ATTEMPTS}',
                        'retry_count': retry_count + 1
                    }
                )
            except Exception as e:
                logger.error(f"Failed to update retry count in database: {str(e)}")
        else:
            # Mark as failed
            self._update_job_status(job_id, 'failed', f'Processing failed: {error}')
    
    def get_queue_length(self) -> int:
        """Get current queue length"""
        return self.redis_client.llen(self.queue_key)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            'queue_length': self.get_queue_length(),
            'processing_count': self.redis_client.scard(self.processing_key),
            'max_concurrent': settings.RAG_MAX_CONCURRENT_PROCESSING
        }
    
    def get_queue_state(self) -> List[Dict[str, Any]]:
        """Get current queue state with job details"""
        queue_jobs = []
        
        # Get queued jobs
        job_ids = self.redis_client.lrange(self.queue_key, 0, -1)
        for job_id in job_ids:
            job_data = self.redis_client.get(f"{self.status_key_prefix}{job_id}")
            if job_data:
                queue_jobs.append(json.loads(job_data))
        
        # Get processing jobs
        processing_ids = self.redis_client.smembers(self.processing_key)
        for job_id in processing_ids:
            job_data = self.redis_client.get(f"{self.status_key_prefix}{job_id}")
            if job_data:
                queue_jobs.append(json.loads(job_data))
        
        return queue_jobs
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            self.redis_client.ping()
            return True
        except:
            return False


def process_document_for_embedding(file_path: str, document_id: str, cancer_type_id: int) -> int:
    """Process a document and create embeddings (synchronous version for direct calls)"""
    try:
        # Load document
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        
        # Generate embeddings
        embeddings_model = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        
        # Process chunks
        chunk_count = 0
        for i, chunk in enumerate(chunks):
            embedding = embeddings_model.embed_query(chunk.page_content)
            
            # Save to database
            response = requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/rag/embeddings/create/",
                headers={'X-Service-Token': settings.DATABASE_SERVICE_TOKEN},
                json={
                    'document_id': document_id,
                    'cancer_type_id': cancer_type_id,
                    'chunk_index': i,
                    'chunk_text': chunk.page_content,
                    'embedding': embedding,
                    'metadata': {
                        'page': chunk.metadata.get('page', 0),
                        'source': chunk.metadata.get('source', '')
                    }
                }
            )
            
            if response.status_code == 201:
                chunk_count += 1
        
        return chunk_count
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise


def query_embeddings(query: str, cancer_type_id: Optional[int] = None, k: int = 5) -> List[Dict[str, Any]]:
    """Query embeddings using vector similarity search"""
    try:
        # Generate query embedding
        embeddings_model = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        query_embedding = embeddings_model.embed_query(query)
        
        # Search via database service
        response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/rag/embeddings/search/",
            headers={'X-Service-Token': settings.DATABASE_SERVICE_TOKEN},
            json={
                'query_embedding': query_embedding,
                'cancer_type_id': cancer_type_id,
                'k': k
            }
        )
        
        if response.status_code == 200:
            return response.json()['results']
        else:
            logger.error(f"Search failed: {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error querying embeddings: {str(e)}")
        return []


def get_processing_status(job_id: str) -> Dict[str, Any]:
    """Get processing status for a job"""
    queue_manager = RedisQueueManager()
    
    # Check Redis first
    job_data = queue_manager.redis_client.get(f"{queue_manager.status_key_prefix}{job_id}")
    if job_data:
        return json.loads(job_data)
    
    # Check database
    try:
        response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/rag/embeddings/status/{job_id}/",
            headers={'X-Service-Token': settings.DATABASE_SERVICE_TOKEN}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'status': 'unknown',
                'message': 'Job not found'
            }
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }


def cleanup_temp_file(file_path: str):
    """Clean up temporary file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {file_path}: {str(e)}")