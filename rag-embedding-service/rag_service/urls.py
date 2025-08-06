"""
URL configuration for rag_service project.
"""
from django.urls import path, include
from rag_app.views import health_check

urlpatterns = [
    path('api/rag/', include('rag_app.urls')),
    path('health/', health_check, name='health_check'),
]