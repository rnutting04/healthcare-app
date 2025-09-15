"""URL configuration for ocr_service project"""
from django.urls import path, include
from ocr_app.views import health_check

urlpatterns = [
    path('health/', health_check, name='health_check'),  # Consistent with other services
    path('api/ocr/', include('ocr_app.urls')),
]