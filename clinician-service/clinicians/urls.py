from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClinicianAuthViewSet, ClinicianProfileView, ClinicianDashboardView

router = DefaultRouter()
router.register(r'clinician/auth', ClinicianAuthViewSet, basename='clinician-auth')

urlpatterns = [
    path('', include(router.urls)),
    path('clinician/auth/profile/', ClinicianProfileView.as_view(), name='clinician-profile'),
    path('clinician/dashboard/', ClinicianDashboardView.as_view(), name='clinician-dashboard'),
]