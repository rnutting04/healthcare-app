from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('logout-all/', views.logout_all, name='logout_all'),
    path('refresh/', views.refresh_token, name='refresh_token'),
    path('verify/', views.verify_token, name='verify_token'),
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('change-password/', views.change_password, name='change_password'),
]