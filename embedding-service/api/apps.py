from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        # Start the queue manager when the app is ready
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Starting embedding service queue manager...")
        
        try:
            from utils.queue_manager import queue_manager
            queue_manager.start()
            logger.info(f"Queue manager started successfully with {queue_manager.max_workers} workers")
        except Exception as e:
            logger.error(f"Failed to start queue manager: {str(e)}")
            # Re-raise to ensure we know about startup failures
            raise