from django.urls import path
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check Redis connection
        cache.set('health_check', 'ok', 1)
        cache_status = cache.get('health_check') == 'ok'
        
        return JsonResponse({
            'status': 'healthy',
            'service': 'database-service',
            'database': 'connected',
            'cache': 'connected' if cache_status else 'disconnected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'service': 'database-service',
            'error': str(e)
        }, status=500)

urlpatterns = [
    path('', health_check, name='health_check'),
]