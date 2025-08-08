"""Service layer for OCR operations"""
import os
import logging
import threading
from pathlib import Path
from typing import Dict, Optional
from django.conf import settings
from .queue_manager import RedisQueueManager
from .ocr_processor import OCRProcessor
from .gpu_detector import GPUDetector
from .exceptions import FileProcessingError, QueueError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import time

logger = logging.getLogger(__name__)


class OCRService:
    """Main service for OCR operations"""
    
    def __init__(self):
        self.queue_manager = RedisQueueManager()
        self.processor = None
        self.processing_thread = None
        self.stop_processing_flag = False
        
    def start_processing(self):
        """Start background processing thread"""
        if not self.processing_thread or not self.processing_thread.is_alive():
            self.stop_processing_flag = False
            self.processing_thread = threading.Thread(target=self._process_queue)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            logger.info("OCR processing thread started")
    
    def stop_processing(self):
        """Stop background processing"""
        self.stop_processing_flag = True
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        logger.info("OCR processing thread stopped")
    
    def submit_job(self, file_path: str, file_name: str, file_type: str, 
                   user_id: int, **kwargs) -> str:
        """
        Submit a new OCR job
        Returns: job_id
        """
        try:
            # Validate file
            if not os.path.exists(file_path):
                raise FileProcessingError(f"File not found: {file_path}")
            
            file_size = os.path.getsize(file_path)
            max_size = settings.OCR_MAX_FILE_SIZE_MB * 1024 * 1024
            
            if file_size > max_size:
                raise FileProcessingError(
                    f"File too large: {file_size / (1024*1024):.2f}MB > {settings.OCR_MAX_FILE_SIZE_MB}MB"
                )
            
            # Create job data
            job_data = {
                'user_id': user_id,
                'file_name': file_name,
                'file_type': file_type,
                'file_size': file_size,
                'file_path': file_path,
                'status': 'pending',
                'progress': 0,
                'message': 'Job queued for processing',
                'ip_address': kwargs.get('ip_address'),
                'user_agent': kwargs.get('user_agent')
            }
            
            # Enqueue job
            job_id = self.queue_manager.enqueue_job(job_data)
            
            # Send initial WebSocket notification
            self._send_websocket_update(job_id, 'queued', 0, 'Job queued for processing')
            
            # Ensure processing thread is running
            self.start_processing()
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to submit OCR job: {str(e)}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status and details"""
        return self.queue_manager.get_job(job_id)
    
    def get_user_jobs(self, user_id: int, limit: int = 10) -> list:
        """Get recent jobs for a user"""
        return self.queue_manager.get_user_jobs(user_id, limit)
    
    def cancel_job(self, job_id: str, user_id: int) -> bool:
        """Cancel a pending or processing job"""
        try:
            job = self.queue_manager.get_job(job_id)
            
            if not job:
                return False
            
            # Verify user owns the job
            if job.get('user_id') != user_id:
                return False
            
            # Only cancel pending or processing jobs
            if job.get('status') not in ['pending', 'processing']:
                return False
            
            # Update job status
            self.queue_manager.update_job(job_id, {
                'status': 'cancelled',
                'message': 'Job cancelled by user'
            })
            
            # Send WebSocket notification
            self._send_websocket_update(job_id, 'cancelled', 0, 'Job cancelled by user')
            
            # Clean up file if exists
            self._cleanup_file(job.get('file_path'))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {str(e)}")
            return False
    
    def get_queue_stats(self) -> Dict:
        """Get queue statistics"""
        stats = self.queue_manager.get_queue_state()
        
        # Add system info
        stats['system'] = GPUDetector.get_system_info()
        stats['max_concurrent_jobs'] = settings.OCR_MAX_CONCURRENT_JOBS
        
        return stats
    
    def _process_queue(self):
        """Background thread to process OCR queue"""
        logger.info("Starting OCR queue processor")
        
        # Initialize OCR processor
        self.processor = OCRProcessor()
        self.processor.initialize_model()
        
        while not self.stop_processing_flag:
            try:
                # Check if we can process more jobs
                processing_count = self.queue_manager.get_processing_count()
                
                if processing_count >= settings.OCR_MAX_CONCURRENT_JOBS:
                    time.sleep(1)
                    continue
                
                # Get next job from queue
                job = self.queue_manager.dequeue_job()
                
                if not job:
                    time.sleep(1)
                    continue
                
                # Process job
                self._process_job(job)
                
            except Exception as e:
                logger.error(f"Error in queue processor: {str(e)}")
                time.sleep(5)
        
        # Cleanup
        if self.processor:
            self.processor.cleanup()
        
        logger.info("OCR queue processor stopped")
    
    def _process_job(self, job: Dict):
        """Process a single OCR job"""
        job_id = job['id']
        file_path = job['file_path']
        
        try:
            logger.info(f"Processing OCR job {job_id}")
            
            # Update job status
            self.queue_manager.update_job(job_id, {
                'status': 'processing',
                'progress': 10,
                'message': 'Starting OCR processing',
                'gpu_detected': self.processor.gpu_available,
                'model_used': self.processor.model_name or 'tesseract'
            })
            
            # Send WebSocket update
            self._send_websocket_update(job_id, 'processing', 10, 'Starting OCR processing')
            
            # Process file
            result = self.processor.process_file(
                file_path=file_path,
                file_type=job['file_type'],
                job_id=job_id
            )
            
            # Update job with results
            self.queue_manager.complete_job(job_id, {
                'extracted_text': result['text'],
                'confidence_score': result.get('confidence', 0),
                'page_count': result.get('page_count', 1),
                'processing_time': result.get('processing_time', 0),
                'model_used': result.get('model_used', 'unknown'),
                'gpu_used': result.get('gpu_used', False)
            })
            
            # Send completion notification
            self._send_websocket_complete(
                job_id=job_id,
                text_preview=result['text'][:500] if result['text'] else '',
                page_count=result.get('page_count', 1),
                confidence=result.get('confidence', 0),
                processing_time=result.get('processing_time', 0)
            )
            
            logger.info(f"OCR job {job_id} completed successfully")
            
            # Schedule file cleanup
            threading.Timer(settings.OCR_CLEANUP_DELAY, self._cleanup_file, [file_path]).start()
            
        except Exception as e:
            logger.error(f"Failed to process OCR job {job_id}: {str(e)}")
            
            # Mark job as failed
            self.queue_manager.fail_job(job_id, str(e))
            
            # Send error notification
            self._send_websocket_error(job_id, str(e))
            
            # Clean up file immediately on error
            self._cleanup_file(file_path)
    
    def _cleanup_file(self, file_path: str):
        """Delete temporary file"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up file {file_path}: {str(e)}")
    
    def _send_websocket_update(self, job_id: str, status: str, progress: int, message: str):
        """Send progress update via WebSocket"""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'ocr_job_{job_id}',
                {
                    'type': 'ocr_progress',
                    'job_id': job_id,
                    'status': status,
                    'progress': progress,
                    'message': message,
                    'timestamp': time.time()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send WebSocket update: {str(e)}")
    
    def _send_websocket_complete(self, job_id: str, text_preview: str, 
                                 page_count: int, confidence: float, processing_time: float):
        """Send completion notification via WebSocket"""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'ocr_job_{job_id}',
                {
                    'type': 'ocr_complete',
                    'job_id': job_id,
                    'message': 'OCR processing completed',
                    'text_preview': text_preview,
                    'page_count': page_count,
                    'confidence': confidence,
                    'processing_time': processing_time,
                    'timestamp': time.time()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send WebSocket completion: {str(e)}")
    
    def _send_websocket_error(self, job_id: str, error: str):
        """Send error notification via WebSocket"""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'ocr_job_{job_id}',
                {
                    'type': 'ocr_error',
                    'job_id': job_id,
                    'message': 'OCR processing failed',
                    'error': error,
                    'timestamp': time.time()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send WebSocket error: {str(e)}")


# Global service instance - will be initialized lazily
_ocr_service = None

def get_ocr_service():
    """Get or create the global OCR service instance"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
        # Start processing thread on first access
        _ocr_service.start_processing()
    return _ocr_service

# For backward compatibility
ocr_service = get_ocr_service