from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .rag_views import RAGChatViewSet

router = DefaultRouter()
router.register(r'profiles', views.PatientViewSet, basename='patient')
router.register(r'appointments', views.AppointmentViewSet, basename='appointment')
router.register(r'medical-records', views.MedicalRecordViewSet, basename='medicalrecord')
router.register(r'prescriptions', views.PrescriptionViewSet, basename='prescription')
router.register(r'languages', views.LanguageViewSet, basename='language')
router.register(r'chat', views.ChatViewSet, basename='chat')
router.register(r'rag-chat', RAGChatViewSet, basename='rag-chat')


urlpatterns = [
    path('', include(router.urls)),
]