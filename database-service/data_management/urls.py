from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'languages', views.LanguageViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'patients', views.PatientViewSet)
router.register(r'clinicians', views.ClinicianViewSet)
router.register(r'cancer-types', views.CancerTypeViewSet)
router.register(r'encryption-keys', views.UserEncryptionKeyViewSet)
router.register(r'files', views.FileMetadataViewSet)
router.register(r'rag-documents', views.RAGDocumentViewSet)
router.register(r'refresh-tokens', views.RefreshTokenViewSet)
router.register(r'patient-assignments', views.PatientAssignmentViewSet)
# RAG Embedding viewsets
router.register(r'rag/embeddings', views.RAGEmbeddingViewSet)
router.register(r'rag/embedding-jobs', views.RAGEmbeddingJobViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('events/', views.log_event, name='log_event'),
    path('statistics/', views.statistics, name='statistics'),
    path('health/', views.health_check, name='health_check'),
    # RAG endpoints
    path('rag/documents/<str:document_id>/has_embeddings/', views.check_document_embeddings, name='check_document_embeddings'),
]