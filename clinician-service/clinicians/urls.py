from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.ClinicianViewSet)
router.register(r'schedules', views.ScheduleViewSet)
router.register(r'patient-assignments', views.PatientAssignmentViewSet)
router.register(r'appointments', views.ClinicianAppointmentViewSet)
router.register(r'medical-notes', views.MedicalNoteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]