from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        # Start the queue manager when the app is ready
        from utils.queue_manager import queue_manager
        queue_manager.start()