from django.urls import path
from .template_views import ClinicianDashboardView

urlpatterns = [
    path('dashboard/', ClinicianDashboardView.as_view(), name='clinician-dashboard-template'),
]