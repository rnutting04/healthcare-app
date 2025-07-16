from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import embedding_api

router = DefaultRouter()
router.register(r'languages', views.LanguageViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'patients', views.PatientViewSet)
# router.register(r'clinicians', views.ClinicianViewSet)
router.register(r'appointments', views.AppointmentViewSet)
router.register(r'medical-records', views.MedicalRecordViewSet)
router.register(r'prescriptions', views.PrescriptionViewSet)
router.register(r'cancer-types', views.CancerTypeViewSet)
router.register(r'encryption-keys', views.UserEncryptionKeyViewSet)
router.register(r'files', views.FileMetadataViewSet)
router.register(r'rag-documents', views.RAGDocumentViewSet)
router.register(r'refresh-tokens', views.RefreshTokenViewSet)
router.register(r'document-embeddings', views.DocumentEmbeddingViewSet)
router.register(r'embedding-chunks', views.EmbeddingChunkViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('events/', views.log_event, name='log_event'),
    path('statistics/', views.statistics, name='statistics'),
    path('health/', views.health_check, name='health_check'),
    # Custom embedding endpoints
    path('embeddings/exists/<str:document_id>/', embedding_api.check_embedding_exists, name='check_embedding_exists'),
    path('embeddings/check-hash/', embedding_api.check_hash_exists, name='check_hash_exists'),
    path('embeddings/store/', embedding_api.store_embeddings, name='store_embeddings'),
    path('embeddings/<str:document_id>/', embedding_api.get_embeddings, name='get_embeddings'),
    path('embeddings/search/', embedding_api.search_similar_documents, name='search_similar'),
    path('embeddings/<str:document_id>/delete/', embedding_api.delete_embeddings, name='delete_embeddings'),
    path('embeddings/user/<int:user_id>/', embedding_api.get_user_embeddings, name='get_user_embeddings'),
    path('embeddings/<str:document_id>/metadata/', embedding_api.update_embedding_metadata, name='update_embedding_metadata'),
]