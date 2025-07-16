from django.urls import path
from .views import (
    ProcessEmbeddingView,
    EmbeddingStatusView,
    DocumentEmbeddingStatusView,
    QueueView,
    SearchSimilarView,
    UserEmbeddingsView
)

urlpatterns = [
    path('process/', ProcessEmbeddingView.as_view(), name='process-embedding'),
    path('status/', EmbeddingStatusView.as_view(), name='embedding-status'),
    path('status/<str:document_id>/', DocumentEmbeddingStatusView.as_view(), name='document-embedding-status'),
    path('queue/', QueueView.as_view(), name='embedding-queue'),
    path('search/', SearchSimilarView.as_view(), name='search-similar'),
    path('user/', UserEmbeddingsView.as_view(), name='user-embeddings'),
]