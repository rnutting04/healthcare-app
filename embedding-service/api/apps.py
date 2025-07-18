from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        # Start the queue manager when the app is ready
        import logging
        import os
        logger = logging.getLogger(__name__)
        logger.info("Starting embedding service queue manager...")
        
        # Log Redis configuration
        redis_url = os.getenv('REDIS_URL', 'Not configured')
        logger.info(f"REDIS_URL configuration: {'Set' if redis_url != 'Not configured' else 'Not set'}")
        
        try:
            from utils.queue_manager import queue_manager
            queue_manager.start()
            
            # Log which backend is being used
            queue_status = queue_manager.get_queue_status()
            backend = queue_status.get('backend', 'unknown')
            logger.info(f"Queue manager started successfully using {backend.upper()} backend")
            logger.info(f"Queue backend details: {queue_status}")
        except Exception as e:
            logger.error(f"Failed to start queue manager: {str(e)}")
            # Re-raise to ensure we know about startup failures
            raise