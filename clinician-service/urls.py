"""
URL configuration for clinician-service project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.generic import RedirectView

schema_view = get_schema_view(
    openapi.Info(
        title="Clinician Service API",
        default_version='v1',
        description="API for managing clinician authentication and profiles",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="admin@healthcare.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Swagger documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API routes
    path('api/', include('clinicians.urls')),
    
    # Template routes
    path('clinician/', include('clinicians.template_urls')),
    
    # Health check
    path('health/', include('clinicians.health_urls')),
    
    # Redirect root to dashboard
    path('', RedirectView.as_view(url='/clinician/dashboard/', permanent=False)),
]