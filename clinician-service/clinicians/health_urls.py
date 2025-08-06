from django.urls import path
from django.http import JsonResponse
from .services import DatabaseService

def health_check(request):
    """Health check endpoint - no authentication required"""
    # Check database service connectivity
    try:
        # Try to make a simple request to database service
        DatabaseService.make_request('GET', '/health/')
        db_status = 'healthy'
    except:
        db_status = 'unhealthy'
    
    return JsonResponse({
        'status': 'healthy',
        'service': 'clinician-service',
        'database_connection': db_status
    })

urlpatterns = [
    path('', health_check, name='health-check'),
]