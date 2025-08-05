"""
URL configuration for rag_service project.
"""
from django.urls import path, include

urlpatterns = [
    path('api/rag/', include('rag_app.urls')),
    path('health/', include('rag_app.urls')),
]