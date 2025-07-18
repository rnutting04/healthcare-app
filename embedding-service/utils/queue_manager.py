import threading
import queue
import logging
import time
import os
import json
import redis
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
            # Initialize Redis connection
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis connection established successfully")
                self.use_redis = True
            except (redis.ConnectionError, AttributeError) as e:
                logger.warning(f"Redis not available, falling back to in-memory queue: {str(e)}")
                self.use_redis = False
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
        
        if self.use_redis:
            # Add to Redis queue
            task_dict = task.to_dict()
            task_json = json.dumps(task_dict)
            # Use priority for scoring (higher priority = lower score = processed first)
            score = time.time() - (priority * 1000)
            self.redis_client.zadd(settings.REDIS_QUEUE_KEY, {task_json: score})
            queue_size = self.redis_client.zcard(settings.REDIS_QUEUE_KEY)
        else:
            # Add to in-memory queue
            self.queue.put(task)
            queue_size = self.queue.qsize()
        
        logger.info(f"Added task to {'Redis' if self.use_redis else 'in-memory'} queue: document_id={document_id}, queue_size={queue_size}, running={self.running}, workers={len(self.workers)}")
        
        return task
    
    def get_task_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific task."""
        if self.use_redis:
            # Check in Redis
            # Check processing
            task_json = self.redis_client.hget(settings.REDIS_PROCESSING_KEY, document_id)
            if task_json:
                return json.loads(task_json)
            
            # Check completed
            task_json = self.redis_client.hget(settings.REDIS_COMPLETED_KEY, document_id)
            if task_json:
                return json.loads(task_json)
            
            # Check failed
            task_json = self.redis_client.hget(settings.REDIS_FAILED_KEY, document_id)
            if task_json:
                return json.loads(task_json)
            
            # Check queue
            queue_items = self.redis_client.zrange(settings.REDIS_QUEUE_KEY, 0, -1)
            for item in queue_items:
                task = json.loads(item)
                if task['document_id'] == document_id:
                    return task
        else:
            # Check in-memory storage
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
        if self.use_redis:
            return {
                'queue_size': self.redis_client.zcard(settings.REDIS_QUEUE_KEY),
                'active_tasks': self.redis_client.hlen(settings.REDIS_PROCESSING_KEY),
                'completed_tasks': self.redis_client.hlen(settings.REDIS_COMPLETED_KEY),
                'failed_tasks': self.redis_client.hlen(settings.REDIS_FAILED_KEY),
                'workers': len(self.workers),
                'running': self.running,
                'stats': self.stats,
                'backend': 'redis'
            }
        else:
            return {
                'queue_size': self.queue.qsize(),
                'active_tasks': len(self.active_tasks),
                'completed_tasks': len(self.completed_tasks),
                'failed_tasks': len(self.failed_tasks),
                'workers': len(self.workers),
                'running': self.running,
                'stats': self.stats,
                'backend': 'in-memory'
            }
    
    def get_queue_items(self) -> List[Dict[str, Any]]:
        """Get all items currently in the queue."""
        items = []
        
        if self.use_redis:
            # Add queued items from Redis
            queue_items = self.redis_client.zrange(settings.REDIS_QUEUE_KEY, 0, -1)
            for i, item in enumerate(queue_items):
                task = json.loads(item)
                task['position'] = i + 1
                items.append(task)
            
            # Add processing items from Redis
            processing_items = self.redis_client.hgetall(settings.REDIS_PROCESSING_KEY)
            for doc_id, task_json in processing_items.items():
                items.append(json.loads(task_json))
        else:
            # Add queued items from memory
            for task in list(self.queue.queue):
                task_dict = task.to_dict()
                task_dict['position'] = len(items) + 1
                items.append(task_dict)
            
            # Add active items from memory
            for task in self.active_tasks.values():
                items.append(task.to_dict())
        
        return items
    
    def _worker(self, worker_id: int):
        """Worker thread that processes embedding tasks."""
        logger.info(f"Worker {worker_id} started, self.running = {self.running}")
        
        loop_count = 0
        while self.running:
            loop_count += 1
            
            try:
                if self.use_redis:
                    # Get task from Redis queue (blocking pop with timeout)
                    result = self.redis_client.bzpopmin(settings.REDIS_QUEUE_KEY, timeout=1)
                    
                    if result is None:
                        continue
                    
                    _, task_json, _ = result
                    task_dict = json.loads(task_json)
                    
                    # Recreate EmbeddingTask from dict
                    task = EmbeddingTask(
                        document_id=task_dict['document_id'],
                        file_path=task_dict['file_path'],
                        file_type=task_dict['file_type'],
                        user_id=task_dict['user_id'],
                        priority=task_dict.get('priority', 0)
                    )
                    task.status = task_dict.get('status', 'queued')
                    task.progress = task_dict.get('progress', 0)
                    
                    logger.info(f"Worker {worker_id} GOT TASK from Redis: {task.document_id} - STARTING PROCESSING")
                    
                    # Store in Redis processing hash
                    task_dict['status'] = 'processing'
                    task_dict['started_at'] = datetime.utcnow().isoformat()
                    task_dict['worker_id'] = worker_id
                    self.redis_client.hset(
                        settings.REDIS_PROCESSING_KEY,
                        task.document_id,
                        json.dumps(task_dict)
                    )
                else:
                    # Get task from in-memory queue
                    # if loop_count % 10 == 0:  # Log every 10 loops
                    #     logger.debug(f"Worker {worker_id} alive, loop {loop_count}, queue size: {self.queue.qsize()}, running: {self.running}")
                    
                    # logger.debug(f"Worker {worker_id} trying to get task from queue")
                    task = self.queue.get(timeout=1)
                    logger.info(f"Worker {worker_id} GOT TASK: {task.document_id} - STARTING PROCESSING")
                    
                    # Move to active tasks
                    self.active_tasks[task.document_id] = task
                
                # Process the task
                self._process_task(task, worker_id)
                
                # Mark task as done (only for in-memory queue)
                if not self.use_redis:
                    self.queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {str(e)}", exc_info=True)
        
        logger.info(f"Worker {worker_id} stopped, final loop count: {loop_count}, self.running = {self.running}")
    
    def _update_task_progress_redis(self, document_id: str, progress: int):
        """Update task progress in Redis."""
        if self.use_redis:
            task_json = self.redis_client.hget(settings.REDIS_PROCESSING_KEY, document_id)
            if task_json:
                task = json.loads(task_json)
                task['progress'] = progress
                task['updated_at'] = datetime.utcnow().isoformat()
                self.redis_client.hset(
                    settings.REDIS_PROCESSING_KEY,
                    document_id,
                    json.dumps(task)
                )
    
    def _process_task(self, task: EmbeddingTask, worker_id: int):
        """Process a single embedding task."""
        logger.info(f"Worker {worker_id} processing task: {task.document_id}")
        
        task.status = 'processing'
        task.started_at = datetime.utcnow()
        
        try:
            # Check if file exists
            if not os.path.exists(task.file_path):
                logger.error(f"File not found: {task.file_path}")
                raise FileNotFoundError(f"File not found: {task.file_path}")
            
            logger.info(f"Processing file: {task.file_path} (exists: {os.path.exists(task.file_path)}, size: {os.path.getsize(task.file_path)})")
            
            # Process document
            task.progress = 10
            if self.use_redis:
                self._update_task_progress_redis(task.document_id, task.progress)
            logger.info(f"Starting document processing for {task.document_id}")
            file_hash, text_chunks, full_text = self.document_processor.process_document(
                task.file_path, task.file_type
            )
            logger.info(f"Document processed: {len(text_chunks)} chunks created")
            
            # Check for duplicate by hash
            if self.db_client.check_hash_exists(file_hash):
                task.status = 'duplicate'
                task.error = 'Document with same content already exists'
                raise ValueError(task.error)
            
            # Generate embeddings
            task.progress = 30
            if self.use_redis:
                self._update_task_progress_redis(task.document_id, task.progress)
            embeddings = self.embedding_generator.generate_embeddings_batch(text_chunks)
            
            # Calculate overall progress based on embeddings generated
            total_chunks = len(text_chunks)
            for i, embedding in enumerate(embeddings):
                if embedding is not None:
                    task.progress = 30 + int((i + 1) / total_chunks * 50)
                    if self.use_redis and i % 5 == 0:  # Update Redis every 5 chunks
                        self._update_task_progress_redis(task.document_id, task.progress)
            
            # Store embeddings in database
            task.progress = 80
            if self.use_redis:
                self._update_task_progress_redis(task.document_id, task.progress)
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
            
            if self.use_redis:
                # Move from processing to failed in Redis
                task_dict = task.to_dict()
                self.redis_client.hdel(settings.REDIS_PROCESSING_KEY, task.document_id)
                self.redis_client.hset(
                    settings.REDIS_FAILED_KEY,
                    task.document_id,
                    json.dumps(task_dict)
                )
                # Set expiry for failed task
                self.redis_client.expire(settings.REDIS_FAILED_KEY, settings.REDIS_TASK_TTL)
            else:
                # Move to failed tasks in memory
                if task.document_id in self.active_tasks:
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