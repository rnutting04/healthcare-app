"""Redis queue manager for OCR jobs"""
import json
import redis
import logging
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class RedisQueueManager:
    """Manages OCR job queue using Redis"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self.queue_key = "ocr:queue"
        self.processing_key = "ocr:processing"
        self.job_prefix = "ocr:job:"
        self.stats_key = "ocr:stats"
        
    def health_check(self) -> bool:
        """Check if Redis is accessible"""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False
    
    def enqueue_job(self, job_data: Dict) -> str:
        """
        Add a job to the queue
        Returns: job_id
        """
        try:
            # Generate job ID if not provided
            job_id = job_data.get('id') or str(uuid.uuid4())
            job_data['id'] = job_id
            job_data['status'] = 'pending'
            job_data['created_at'] = datetime.utcnow().isoformat()
            job_data['position'] = self.get_queue_length() + 1
            
            # Store job data
            job_key = f"{self.job_prefix}{job_id}"
            self.redis_client.setex(
                job_key,
                settings.OCR_JOB_TIMEOUT + 3600,  # Keep for 1 hour after timeout
                json.dumps(job_data)
            )
            
            # Add to queue
            self.redis_client.rpush(self.queue_key, job_id)
            
            # Update stats
            self.redis_client.hincrby(self.stats_key, 'total_queued', 1)
            
            logger.info(f"Job {job_id} enqueued successfully")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue job: {str(e)}")
            raise
    
    def dequeue_job(self) -> Optional[Dict]:
        """
        Get next job from queue (FIFO)
        Returns: job_data or None
        """
        try:
            # Move job from queue to processing
            job_id = self.redis_client.brpoplpush(
                self.queue_key,
                self.processing_key,
                timeout=1
            )
            
            if not job_id:
                return None
            
            # Get job data
            job_key = f"{self.job_prefix}{job_id}"
            job_data = self.redis_client.get(job_key)
            
            if not job_data:
                # Job data missing, remove from processing
                self.redis_client.lrem(self.processing_key, 0, job_id)
                return None
            
            job = json.loads(job_data)
            job['started_at'] = datetime.utcnow().isoformat()
            job['status'] = 'processing'
            
            # Update job data
            self.redis_client.setex(
                job_key,
                settings.OCR_JOB_TIMEOUT + 3600,
                json.dumps(job)
            )
            
            # Update stats
            self.redis_client.hincrby(self.stats_key, 'total_processing', 1)
            
            logger.info(f"Job {job_id} dequeued for processing")
            return job
            
        except Exception as e:
            logger.error(f"Failed to dequeue job: {str(e)}")
            return None
    
    def update_job(self, job_id: str, updates: Dict) -> bool:
        """Update job data"""
        try:
            job_key = f"{self.job_prefix}{job_id}"
            job_data = self.redis_client.get(job_key)
            
            if not job_data:
                logger.warning(f"Job {job_id} not found for update")
                return False
            
            job = json.loads(job_data)
            job.update(updates)
            job['updated_at'] = datetime.utcnow().isoformat()
            
            # Set appropriate TTL based on status
            if job.get('status') in ['completed', 'failed', 'cancelled']:
                ttl = 3600  # Keep completed jobs for 1 hour
            else:
                ttl = settings.OCR_JOB_TIMEOUT + 3600
            
            self.redis_client.setex(job_key, ttl, json.dumps(job))
            
            logger.info(f"Job {job_id} updated with status: {job.get('status')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {str(e)}")
            return False
    
    def complete_job(self, job_id: str, result: Dict) -> bool:
        """Mark job as completed"""
        try:
            # Remove from processing
            self.redis_client.lrem(self.processing_key, 0, job_id)
            
            # Update job data
            updates = {
                'status': 'completed',
                'completed_at': datetime.utcnow().isoformat(),
                'result': result
            }
            
            success = self.update_job(job_id, updates)
            
            if success:
                # Update stats
                self.redis_client.hincrby(self.stats_key, 'total_completed', 1)
                self.redis_client.hincrby(self.stats_key, 'total_processing', -1)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {str(e)}")
            return False
    
    def fail_job(self, job_id: str, error: str) -> bool:
        """Mark job as failed"""
        try:
            # Remove from processing
            self.redis_client.lrem(self.processing_key, 0, job_id)
            
            # Update job data
            updates = {
                'status': 'failed',
                'failed_at': datetime.utcnow().isoformat(),
                'error': error
            }
            
            success = self.update_job(job_id, updates)
            
            if success:
                # Update stats
                self.redis_client.hincrby(self.stats_key, 'total_failed', 1)
                self.redis_client.hincrby(self.stats_key, 'total_processing', -1)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to mark job {job_id} as failed: {str(e)}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job data by ID"""
        try:
            job_key = f"{self.job_prefix}{job_id}"
            job_data = self.redis_client.get(job_key)
            
            if not job_data:
                return None
            
            return json.loads(job_data)
            
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {str(e)}")
            return None
    
    def get_queue_length(self) -> int:
        """Get number of jobs in queue"""
        try:
            return self.redis_client.llen(self.queue_key)
        except Exception as e:
            logger.error(f"Failed to get queue length: {str(e)}")
            return 0
    
    def get_processing_count(self) -> int:
        """Get number of jobs being processed"""
        try:
            return self.redis_client.llen(self.processing_key)
        except Exception as e:
            logger.error(f"Failed to get processing count: {str(e)}")
            return 0
    
    def get_queue_state(self) -> Dict:
        """Get current queue state"""
        try:
            stats = self.redis_client.hgetall(self.stats_key)
            
            return {
                'pending': self.get_queue_length(),
                'processing': self.get_processing_count(),
                'total_queued': int(stats.get('total_queued', 0)),
                'total_processing': int(stats.get('total_processing', 0)),
                'total_completed': int(stats.get('total_completed', 0)),
                'total_failed': int(stats.get('total_failed', 0))
            }
        except Exception as e:
            logger.error(f"Failed to get queue state: {str(e)}")
            return {
                'pending': 0,
                'processing': 0,
                'total_queued': 0,
                'total_processing': 0,
                'total_completed': 0,
                'total_failed': 0
            }
    
    def get_user_jobs(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent jobs for a user"""
        try:
            # Get all job keys
            pattern = f"{self.job_prefix}*"
            job_keys = self.redis_client.keys(pattern)
            
            user_jobs = []
            for key in job_keys:
                job_data = self.redis_client.get(key)
                if job_data:
                    job = json.loads(job_data)
                    if job.get('user_id') == user_id:
                        user_jobs.append(job)
            
            # Sort by created_at descending
            user_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return user_jobs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get user jobs: {str(e)}")
            return []
    
    def cleanup_old_jobs(self, hours: int = 24) -> int:
        """Clean up jobs older than specified hours"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            pattern = f"{self.job_prefix}*"
            job_keys = self.redis_client.keys(pattern)
            
            deleted = 0
            for key in job_keys:
                job_data = self.redis_client.get(key)
                if job_data:
                    job = json.loads(job_data)
                    created_at = datetime.fromisoformat(job.get('created_at', datetime.utcnow().isoformat()))
                    
                    if created_at < cutoff and job.get('status') in ['completed', 'failed', 'cancelled']:
                        self.redis_client.delete(key)
                        deleted += 1
            
            logger.info(f"Cleaned up {deleted} old jobs")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {str(e)}")
            return 0