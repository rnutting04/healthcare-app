from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('admin/dashboard/', views.dashboard, name='admin_dashboard'),
    
    # Cancer Types
    path('admin/cancer-types/', views.cancer_types_list, name='cancer_types_list'),
    path('admin/cancer-types/create/', views.cancer_type_create, name='cancer_type_create'),
    path('admin/cancer-types/<int:cancer_type_id>/edit/', views.cancer_type_edit, name='cancer_type_edit'),
    path('admin/cancer-types/<int:cancer_type_id>/delete/', views.cancer_type_delete, name='cancer_type_delete'),
    
    
    # User Management
    path('admin/users/', views.users_list, name='users_list'),
    path('admin/users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('admin/users/<int:user_id>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
    
    # Patient Management
    path('admin/patients/<int:patient_id>/update/', views.update_patient_info, name='update_patient_info'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
]