"""Refactored views for RAG embedding service"""
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings

from .decorators import handle_exceptions, require_auth
from .exceptions import ValidationError
from .services import EmbeddingService, ChatService
from .utils import RedisQueueManager
from .auth import verify_jwt_token  # Import for backward compatibility

logger = logging.getLogger(__name__)


@api_view(['POST'])
@handle_exceptions
@require_auth
def process_embedding(request):
    """Submit file for embedding processing"""
    # Validate required fields
    document_id = request.data.get('document_id')
    cancer_type_id = request.data.get('cancer_type_id')
    
    if not document_id:
        raise ValidationError("document_id is required")
    if not cancer_type_id:
        raise ValidationError("cancer_type_id is required")
    
    # Get JWT token for downstream services
    jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # Process document
    embedding_service = EmbeddingService()
    result = embedding_service.process_document(
        document_id=document_id,
        cancer_type_id=cancer_type_id,
        user_id=request.user_id,
        jwt_token=jwt_token
    )
    
    return Response({
        'success': True,
        'message': 'Document queued for embedding processing',
        **result
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@handle_exceptions
@require_auth
def get_embedding_status(request, job_id=None):
    """Get embedding processing status"""
    embedding_service = EmbeddingService()
    
    if job_id:
        # Get specific job status
        status_info = embedding_service.get_job_status(job_id)
        return Response({
            'success': True,
            'job_id': job_id,
            'status': status_info
        })
    else:
        # Get overall statistics
        stats = embedding_service.get_queue_stats()
        return Response({
            'success': True,
            'statistics': stats
        })


@api_view(['GET'])
@handle_exceptions
@require_auth
def get_queue_status(request):
    """Get current queue state"""
    queue_manager = RedisQueueManager()
    queue_state = queue_manager.get_queue_state()
    
    return Response({
        'success': True,
        'queue': queue_state
    })


@api_view(['POST'])
@handle_exceptions
@require_auth  
def query_rag(request):
    """Query the RAG system"""
    # Validate required fields
    query = request.data.get('query')
    if not query:
        raise ValidationError("Query text is required")
    
    # Get optional parameters
    cancer_type_id = request.data.get('cancer_type_id')
    session_id = request.data.get('session_id')
    
    # Process query
    result = ChatService.process_query(
        query=query,
        cancer_type_id=cancer_type_id,
        language=request.data.get('language', 'English'),
        session_id=session_id,
        user_id=request.user_id,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )
    
    return Response(result)


@api_view(['POST'])
@handle_exceptions
@require_auth
def clear_session(request):
    """Clear chat session history"""
    session_id = request.data.get('session_id')
    if not session_id:
        raise ValidationError("Session ID is required")
    
    ChatService.clear_session(session_id)
    
    return Response({
        'success': True,
        'message': 'Session history cleared',
        'session_id': session_id
    })


@api_view(['GET'])
@handle_exceptions
def health_check(request):
    """Health check endpoint"""
    queue_manager = RedisQueueManager()
    
    # Check components
    redis_healthy = queue_manager.health_check()
    openai_configured = bool(settings.OPENAI_API_KEY)
    
    # Check database service
    try:
        import requests
        from .services import DatabaseService
        response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/health/",
            headers=DatabaseService.get_headers(),
            timeout=5
        )
        db_healthy = response.status_code == 200
    except:
        db_healthy = False
    
    all_healthy = redis_healthy and db_healthy and openai_configured
    
    return Response({
        'status': 'healthy' if all_healthy else 'unhealthy',
        'service': 'rag-embedding-service',
        'timestamp': timezone.now().isoformat(),
        'checks': {
            'redis': redis_healthy,
            'database_service': db_healthy,
            'openai_configured': openai_configured
        }
    }, status=200 if all_healthy else 503)
