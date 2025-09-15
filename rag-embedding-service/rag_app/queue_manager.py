"""Redis queue management for document processing"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, List
import redis
import requests
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .exceptions import QueueError, ProcessingError
from .document_processor import DocumentProcessor

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
        self.worker_thread = None
        self.channel_layer = get_channel_layer()
        self.document_processor = DocumentProcessor()
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
            settings.RAG_PROCESSING_TIMEOUT * 2,
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
                job_id = self._get_next_job()
                if job_id:
                    self._process_single_job(job_id)
            except Exception as e:
                logger.error(f"Queue worker error: {str(e)}")
                time.sleep(5)
    
    def _get_next_job(self) -> str:
        """Get next job from queue if processing capacity available"""
        # Check for jobs
        result = self.redis_client.blpop(self.queue_key, timeout=5)
        if not result:
            return None
            
        job_id = result[1]
        
        # Check concurrent processing limit
        processing_count = self.redis_client.scard(self.processing_key)
        if processing_count >= settings.RAG_MAX_CONCURRENT_PROCESSING:
            # Put back in queue and wait
            self.redis_client.lpush(self.queue_key, job_id)
            time.sleep(5)
            return None
        
        return job_id
    
    def _process_single_job(self, job_id: str):
        """Process a single job"""
        # Get job data
        job_data = self._get_job_data(job_id)
        if not job_data:
            logger.error(f"Job {job_id} data not found")
            return
        
        # Mark as processing
        self.redis_client.sadd(self.processing_key, job_id)
        self._update_job_status(job_id, 'processing', 'Starting document processing')
        
        try:
            # Process the document
            self.document_processor.process_job(job_data, self._update_job_status)
            self._update_job_status(job_id, 'completed', 'Document processed successfully')
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            self._handle_job_failure(job_id, job_data, str(e))
        finally:
            # Remove from processing set
            self.redis_client.srem(self.processing_key, job_id)
    
    def _get_job_data(self, job_id: str) -> Dict[str, Any]:
        """Get job data from Redis"""
        data = self.redis_client.get(f"{self.status_key_prefix}{job_id}")
        return json.loads(data) if data else None
    
    def _update_job_status(self, job_id: str, status: str, message: str, progress_data: dict = None):
        """Update job status in Redis and database"""
        # Update Redis
        job_data = self._get_job_data(job_id)
        if job_data:
            job_data.update({
                'status': status,
                'message': message,
                'updated_at': datetime.now().isoformat()
            })
            if progress_data:
                job_data['progress'] = progress_data
                
            self.redis_client.setex(
                f"{self.status_key_prefix}{job_id}",
                settings.RAG_PROCESSING_TIMEOUT * 2,
                json.dumps(job_data)
            )
        
        # Update database
        self._update_database_job(job_id, status, message, progress_data)
        
        # Send WebSocket update
        self._send_websocket_update(job_id, status, message, progress_data)
    
    def _update_database_job(self, job_id: str, status: str, message: str, progress_data: dict = None):
        """Update job status in database"""
        try:
            headers = {'X-Service-Token': settings.DATABASE_SERVICE_TOKEN}
            
            # Format message with progress data if available
            if progress_data:
                message_data = {'text': message, 'progress': progress_data}
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
                headers=headers,
                json=update_data
            )
        except Exception as e:
            logger.error(f"Failed to update job status in database: {str(e)}")
    
    def _send_websocket_update(self, job_id: str, status: str, message: str, progress_data: dict = None):
        """Send real-time update via WebSocket"""
        try:
            group_name = f'embedding_job_{job_id}'
            
            websocket_data = {
                'type': 'embedding_progress',
                'job_id': job_id,
                'status': status,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            if progress_data:
                websocket_data['progress'] = progress_data
            
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
            
            # Update status
            self._update_job_status(
                job_id, 'retrying',
                f'Retry attempt {retry_count + 1} of {settings.RAG_RETRY_MAX_ATTEMPTS}'
            )
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
            job_data = self._get_job_data(job_id)
            if job_data:
                queue_jobs.append(job_data)
        
        # Get processing jobs
        processing_ids = self.redis_client.smembers(self.processing_key)
        for job_id in processing_ids:
            job_data = self._get_job_data(job_id)
            if job_data:
                queue_jobs.append(job_data)
        
        return queue_jobs
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            self.redis_client.ping()
            return True
        except:
            return False