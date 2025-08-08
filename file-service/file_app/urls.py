from django.urls import path
from . import views

urlpatterns = [
    path('files/upload', views.upload_file, name='upload_file'),
    path('files/upload/medical-record', views.upload_medical_record, name='upload_medical_record'),
    path('files/user', views.list_user_files, name='list_user_files'),
    path('files/<str:file_id>', views.download_file, name='download_file'),
    path('files/<str:file_id>/delete', views.delete_user_file, name='delete_file'),
    path('files/medical-records/<str:file_id>/delete', views.delete_medical_record, name='delete_medical_record'),
    path('files/medical-records/<str:file_id>/download', views.download_medical_record, name='download_medical_record'),
    path('health/', views.health_check, name='health_check'),
]