from django.urls import path
from . import views

urlpatterns = [
    path('files/upload', views.upload_file, name='upload_file'),
    path('files/user', views.list_user_files, name='list_user_files'),
    path('files/<str:file_id>', views.download_file, name='download_file'),
    path('files/<str:file_id>/delete', views.delete_user_file, name='delete_file'),
    path('health/', views.health_check, name='health_check'),
]