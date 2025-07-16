"""
URL configuration for embedding project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('embeddings/', include('api.urls')),
    path('health/', include('api.health_urls')),
]