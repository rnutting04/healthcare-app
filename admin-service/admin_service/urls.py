"""admin_service URL Configuration"""
from django.urls import path, include

urlpatterns = [
    # Removed Django admin as we're using custom admin interface
    path('', include('admin_app.urls')),
]