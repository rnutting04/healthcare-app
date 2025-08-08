"""URL configuration for OCR app"""
from django.urls import path
from . import views

urlpatterns = [
    # OCR job management - ALL REQUIRE AUTHENTICATION
    path('submit/', views.submit_ocr_job, name='submit_ocr_job'),
    path('job/<str:job_id>/status/', views.get_job_status, name='get_job_status'),
    path('job/<str:job_id>/result/', views.get_job_result, name='get_job_result'),
    path('job/<str:job_id>/cancel/', views.cancel_job, name='cancel_job'),
    path('jobs/', views.get_user_jobs, name='get_user_jobs'),
    
    # Statistics and info - ALL REQUIRE AUTHENTICATION
    path('stats/', views.get_queue_stats, name='get_queue_stats'),
    path('system/', views.get_system_info, name='get_system_info'),
]