import threading
import queue
import logging
import time
import os
from typing import Dict, Optional, Any, List
from datetime import datetime
from django.conf import settings
from utils.document_processor import DocumentProcessor
from utils.embedding_generator import EmbeddingGenerator
from utils.database_client import DatabaseClient

logger = logging.getLogger('embedding')


class EmbeddingTask:
    """Represents a single embedding task in the queue."""
    
    def __init__(self, document_id: str, file_path: str, file_type: str, 
                 user_id: str, priority: int = 0):
        self.document_id = document_id
        self.file_path = file_path
        self.file_type = file_type
        self.user_id = user_id
        self.priority = priority
        self.submitted_at = datetime.utcnow()
        self.status = 'queued'
        self.progress = 0
        self.error = None
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for API responses."""
        return {
            'document_id': self.document_id,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'user_id': self.user_id,
            'priority': self.priority,
            'status': self.status,
            'progress': self.progress,
            'error': self.error,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': (self.completed_at - self.started_at).total_seconds() if self.completed_at and self.started_at else None
        }


class QueueManager:
    """Manages the FIFO queue for embedding processing."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.queue = queue.Queue()
            self.active_tasks = {}
            self.completed_tasks = {}
            self.failed_tasks = {}
            self.workers = []
            self.running = False
            self.document_processor = DocumentProcessor()
            self.embedding_generator = EmbeddingGenerator()
            self.db_client = DatabaseClient()
            self.initialized = True
            self.stats = {
                'total_processed': 0,
                'total_failed': 0,
                'total_chunks_processed': 0,
                'average_processing_time': 0
            }
    
    def start(self):
        """Start the queue workers."""
        if self.running:
            logger.warning("Queue manager already running, skipping start")
            return
        
        self.running = True
        logger.info(f"Setting self.running = {self.running}")
        
        # Start worker threads
        for i in range(settings.MAX_CONCURRENT_EMBEDDINGS):
            worker = threading.Thread(target=self._worker, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
            logger.info(f"Started worker thread {i}")
        
        logger.info(f"Started {settings.MAX_CONCURRENT_EMBEDDINGS} embedding workers, self.running = {self.running}")
    
    def stop(self):
        """Stop the queue workers."""
        self.running = False
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers = []
        logger.info("Stopped all embedding workers")
    
    def add_task(self, document_id: str, file_path: str, file_type: str, 
                 user_id: str, priority: int = 0) -> EmbeddingTask:
        """Add a new embedding task to the queue."""
        task = EmbeddingTask(document_id, file_path, file_type, user_id, priority)
        
        # Check if document already exists
        if self.db_client.check_embedding_exists(document_id):
            task.status = 'duplicate'
            task.error = 'Document already has embeddings'
            self.failed_tasks[document_id] = task
            logger.info(f"Document {document_id} already has embeddings, skipping")
            return task
        
        self.queue.put(task)
        logger.info(f"Added task to queue: document_id={document_id}, queue_size={self.queue.qsize()}, running={self.running}, workers={len(self.workers)}")
        
        return task
    
    def get_task_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific task."""
        # Check active tasks
        if document_id in self.active_tasks:
            return self.active_tasks[document_id].to_dict()
        
        # Check completed tasks
        if document_id in self.completed_tasks:
            return self.completed_tasks[document_id].to_dict()
        
        # Check failed tasks
        if document_id in self.failed_tasks:
            return self.failed_tasks[document_id].to_dict()
        
        # Check queue
        for task in list(self.queue.queue):
            if task.document_id == document_id:
                return task.to_dict()
        
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status."""
        return {
            'queue_size': self.queue.qsize(),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'workers': len(self.workers),
            'running': self.running,
            'stats': self.stats
        }
    
    def get_queue_items(self) -> List[Dict[str, Any]]:
        """Get all items currently in the queue."""
        items = []
        
        # Add queued items
        for task in list(self.queue.queue):
            task_dict = task.to_dict()
            task_dict['position'] = len(items) + 1
            items.append(task_dict)
        
        # Add active items
        for task in self.active_tasks.values():
            items.append(task.to_dict())
        
        return items
    
    def _worker(self, worker_id: int):
        """Worker thread that processes embedding tasks."""
        logger.info(f"Worker {worker_id} started, self.running = {self.running}")
        
        loop_count = 0
        while self.running:
            loop_count += 1
            if loop_count % 10 == 0:  # Log every 10 loops
                logger.debug(f"Worker {worker_id} alive, loop {loop_count}, queue size: {self.queue.qsize()}, running: {self.running}")
            
            try:
                # Get task from queue with timeout
                task = self.queue.get(timeout=1)
                logger.info(f"Worker {worker_id} got task: {task.document_id}")
                
                # Move to active tasks
                self.active_tasks[task.document_id] = task
                
                # Process the task
                self._process_task(task, worker_id)
                
                # Mark task as done
                self.queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {str(e)}", exc_info=True)
        
        logger.info(f"Worker {worker_id} stopped, final loop count: {loop_count}, self.running = {self.running}")
    
    def _process_task(self, task: EmbeddingTask, worker_id: int):
        """Process a single embedding task."""
        logger.info(f"Worker {worker_id} processing task: {task.document_id}")
        
        task.status = 'processing'
        task.started_at = datetime.utcnow()
        
        try:
            # Process document
            task.progress = 10
            file_hash, text_chunks, full_text = self.document_processor.process_document(
                task.file_path, task.file_type
            )
            
            # Check for duplicate by hash
            if self.db_client.check_hash_exists(file_hash):
                task.status = 'duplicate'
                task.error = 'Document with same content already exists'
                raise ValueError(task.error)
            
            # Generate embeddings
            task.progress = 30
            embeddings = self.embedding_generator.generate_embeddings_batch(text_chunks)
            
            # Calculate overall progress based on embeddings generated
            total_chunks = len(text_chunks)
            for i, embedding in enumerate(embeddings):
                if embedding is not None:
                    task.progress = 30 + int((i + 1) / total_chunks * 50)
            
            # Store embeddings in database
            task.progress = 80
            success = self.db_client.store_embeddings(
                document_id=task.document_id,
                file_hash=file_hash,
                embeddings=embeddings,
                text_chunks=text_chunks,
                user_id=task.user_id,
                metadata={
                    'file_type': task.file_type,
                    'total_chunks': len(text_chunks),
                    'model': settings.OPENAI_EMBEDDING_MODEL
                }
            )
            
            if not success:
                raise Exception("Failed to store embeddings in database")
            
            # Delete the file after successful processing
            task.progress = 95
            try:
                os.remove(task.file_path)
                logger.info(f"Deleted processed file: {task.file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {task.file_path}: {str(e)}")
            
            # Mark as completed
            task.status = 'completed'
            task.progress = 100
            task.completed_at = datetime.utcnow()
            
            # Update stats
            self.stats['total_processed'] += 1
            self.stats['total_chunks_processed'] += len(text_chunks)
            processing_time = (task.completed_at - task.started_at).total_seconds()
            self.stats['average_processing_time'] = (
                (self.stats['average_processing_time'] * (self.stats['total_processed'] - 1) + processing_time) /
                self.stats['total_processed']
            )
            
            # Move to completed tasks
            del self.active_tasks[task.document_id]
            self.completed_tasks[task.document_id] = task
            
            logger.info(f"Successfully processed document {task.document_id}")
            
        except Exception as e:
            logger.error(f"Failed to process document {task.document_id}: {str(e)}")
            
            task.status = 'failed'
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            
            # Update stats
            self.stats['total_failed'] += 1
            
            # Move to failed tasks
            del self.active_tasks[task.document_id]
            self.failed_tasks[task.document_id] = task
            
            # Optionally delete the file on failure (based on error type)
            if 'duplicate' not in str(e).lower():
                try:
                    os.remove(task.file_path)
                    logger.info(f"Deleted failed file: {task.file_path}")
                except Exception as del_e:
                    logger.error(f"Failed to delete file {task.file_path}: {str(del_e)}")


# Global queue manager instance
queue_manager = QueueManager()