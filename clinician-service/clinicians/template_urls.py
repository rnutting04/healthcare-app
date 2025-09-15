from django.urls import path
from .template_views import ClinicianDashboardView, PatientDashboardView, AddMedicalRecordView

urlpatterns = [
    path('dashboard/', ClinicianDashboardView.as_view(), name='clinician-dashboard-template'),
    path('patients/<int:patient_id>/dashboard/', PatientDashboardView.as_view(), name='patient-dashboard-template'),
    path('patients/<int:patient_id>/add-record/', AddMedicalRecordView.as_view(), name='add-medical-record-template'),
]