from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'languages', views.LanguageViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'patients', views.PatientViewSet)
router.register(r'clinicians', views.ClinicianViewSet)
router.register(r'appointments', views.AppointmentViewSet)
router.register(r'medical-records', views.MedicalRecordViewSet)
router.register(r'prescriptions', views.PrescriptionViewSet)
router.register(r'cancer-types', views.CancerTypeViewSet)
router.register(r'encryption-keys', views.UserEncryptionKeyViewSet)
router.register(r'files', views.FileMetadataViewSet)
router.register(r'rag-documents', views.RAGDocumentViewSet)
router.register(r'refresh-tokens', views.RefreshTokenViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('events/', views.log_event, name='log_event'),
    path('statistics/', views.statistics, name='statistics'),
    path('health/', views.health_check, name='health_check'),
]