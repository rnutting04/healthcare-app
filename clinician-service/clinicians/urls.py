from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClinicianAuthViewSet, ClinicianProfileView, ClinicianDashboardView, 
    ClinicianPatientsView, PatientDetailView, PatientDashboardView,
    MedicalRecordDownloadView, MedicalRecordDeleteView, MedicalRecordViewView,
    TempFileCleanupView
)

router = DefaultRouter()
router.register(r'clinician/auth', ClinicianAuthViewSet, basename='clinician-auth')

urlpatterns = [
    path('', include(router.urls)),
    path('clinician/auth/profile/', ClinicianProfileView.as_view(), name='clinician-profile'),
    path('clinician/dashboard/', ClinicianDashboardView.as_view(), name='clinician-dashboard'),
    path('clinician/patients/', ClinicianPatientsView.as_view(), name='clinician-patients'),
    path('clinician/patients/<int:patient_id>/', PatientDetailView.as_view(), name='patient-detail'),
    path('clinician/patients/<int:patient_id>/dashboard/', PatientDashboardView.as_view(), name='patient-dashboard'),
    
    # Medical record endpoints
    path('files/medical-records/<str:file_id>/download/', MedicalRecordDownloadView.as_view(), name='medical-record-download'),
    path('files/medical-records/<str:file_id>/delete/', MedicalRecordDeleteView.as_view(), name='medical-record-delete'),
    path('files/medical-records/<str:file_id>/view/', MedicalRecordViewView.as_view(), name='medical-record-view'),
    path('files/temp/cleanup/', TempFileCleanupView.as_view(), name='temp-file-cleanup'),
]