from django.urls import path
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis
from django.conf import settings

def health_check(request):
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check Redis connection
        cache.set('health_check', 'ok', 1)
        cache.get('health_check')
        
        return JsonResponse({
            'status': 'healthy',
            'service': 'auth-service',
            'database': 'connected',
            'cache': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'service': 'auth-service',
            'error': str(e)
        }, status=500)

urlpatterns = [
    path('', health_check, name='health_check'),
]