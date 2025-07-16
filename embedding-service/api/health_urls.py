from django.urls import path
from django.http import JsonResponse

def health_check(request):
    """Health check endpoint."""
    return JsonResponse({'status': 'healthy', 'service': 'embedding-service'})

urlpatterns = [
    path('', health_check, name='health-check'),
]