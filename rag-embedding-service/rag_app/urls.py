from django.urls import path
from . import views

urlpatterns = [
    # Embedding endpoints
    path('embeddings/process/', views.process_embedding, name='process_embedding'),
    path('embeddings/status/', views.get_embedding_status, name='embedding_status'),
    path('embeddings/status/<str:job_id>/', views.get_embedding_status, name='embedding_status_detail'),
    path('embeddings/queue/', views.get_queue_status, name='queue_status'),
    
    # Query endpoints
    path('chat/query/', views.query_rag, name='query_rag'),
    path('chat/clear-session/', views.clear_session, name='clear_session'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
]