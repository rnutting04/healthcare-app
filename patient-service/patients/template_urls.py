from django.urls import path
from . import template_views

urlpatterns = [
    path('patient/dashboard/', template_views.patient_dashboard, name='patient_dashboard'),
    path('patient/profile/edit/', template_views.patient_profile_edit, name='patient_profile_edit'),
    path('patient/appointments/', template_views.patient_appointments, name='patient_appointments'),
    path('patient/records/', template_views.patient_records, name='patient_records'),
    path('patient/prescriptions/', template_views.patient_prescriptions, name='patient_prescriptions'),
]