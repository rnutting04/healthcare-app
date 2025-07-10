from django.urls import path
from . import template_views

urlpatterns = [
    path('clinician/dashboard/', template_views.clinician_dashboard, name='clinician_dashboard'),
    path('clinician/appointments/', template_views.clinician_appointments, name='clinician_appointments'),
    path('clinician/patients/', template_views.clinician_patients, name='clinician_patients'),
    path('clinician/schedule/', template_views.clinician_schedule, name='clinician_schedule'),
]