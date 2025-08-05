import os
import uuid
import logging
import json
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import jwt
import requests
from .utils import (
    RedisQueueManager,
    process_document_for_embedding,
    query_embeddings,
    get_processing_status,
    cleanup_temp_file
)

logger = logging.getLogger(__name__)


def verify_jwt_token(request):
    """Verify JWT token and extract user information"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, "No authorization token provided"
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"


def get_db_headers():
    """Get authentication headers for database service"""
    return {
        'X-Service-Token': settings.DATABASE_SERVICE_TOKEN
    }


def get_file_from_file_service(file_id, jwt_token):
    """Download file from file service"""
    try:
        headers = {
            'Authorization': f'Bearer {jwt_token}'
        }
        response = requests.get(
            f"{settings.FILE_SERVICE_URL}/api/files/{file_id}",
            headers=headers,
            stream=True
        )
        if response.status_code == 200:
            # Save to temp file
            temp_path = os.path.join(settings.TEMP_FILE_PATH, f"{file_id}.pdf")
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return temp_path, None
        else:
            return None, f"Failed to download file: {response.status_code}"
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return None, str(e)


@api_view(['POST'])
@csrf_exempt
def process_embedding(request):
    """Submit file for embedding processing"""
    # Verify JWT token
    payload, error = verify_jwt_token(request)
    if error:
        return Response({
            'success': False,
            'error': error,
            'message': 'Authentication failed'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    user_id = payload.get('user_id')
    
    # Get document ID and cancer type from request
    document_id = request.data.get('document_id')
    cancer_type_id = request.data.get('cancer_type_id')
    
    if not document_id:
        return Response({
            'success': False,
            'error': 'Missing document_id',
            'message': 'document_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not cancer_type_id:
        return Response({
            'success': False,
            'error': 'Missing cancer_type_id',
            'message': 'cancer_type_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Check if document already has embeddings
        check_response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/rag/documents/{document_id}/has_embeddings/",
            headers=get_db_headers()
        )
        
        if check_response.status_code == 200 and check_response.json().get('has_embeddings'):
            return Response({
                'success': False,
                'error': 'Document already processed',
                'message': 'This document already has embeddings'
            }, status=status.HTTP_409_CONFLICT)
        
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Get JWT token for file service
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        # Initialize Redis queue manager
        queue_manager = RedisQueueManager()
        
        # Add job to queue
        job_data = {
            'job_id': job_id,
            'document_id': document_id,
            'cancer_type_id': cancer_type_id,
            'user_id': user_id,
            'jwt_token': jwt_token,
            'created_at': datetime.now().isoformat()
        }
        
        queue_manager.add_job(job_data)
        
        # Create embedding job in database using the create_status action
        job_response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/rag/embedding-jobs/create_status/",
            headers=get_db_headers(),
            json={
                'job_id': job_id,
                'document_id': document_id,
                'status': 'pending',
                'message': 'Job queued for processing'
            }
        )
        
        if job_response.status_code not in [200, 201]:
            logger.error(f"Failed to create embedding job: {job_response.text}")
        
        return Response({
            'success': True,
            'message': 'Document queued for embedding processing',
            'job_id': job_id,
            'document_id': document_id,
            'queue_position': queue_manager.get_queue_length()
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error submitting embedding job: {str(e)}")
        return Response({
            'success': False,
            'error': 'Processing failed',
            'message': 'Failed to submit document for processing'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_embedding_status(request, job_id=None):
    """Get embedding processing status"""
    # Verify JWT token
    payload, error = verify_jwt_token(request)
    if error:
        return Response({
            'success': False,
            'error': error,
            'message': 'Authentication failed'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        if job_id:
            # Get specific job status
            status_info = get_processing_status(job_id)
            return Response({
                'success': True,
                'job_id': job_id,
                'status': status_info
            })
        else:
            # Get overall queue status
            queue_manager = RedisQueueManager()
            stats = queue_manager.get_queue_stats()
            
            # Get processing statistics from database
            stats_response = requests.get(
                f"{settings.DATABASE_SERVICE_URL}/api/rag/embeddings/statistics/",
                headers=get_db_headers()
            )
            
            if stats_response.status_code == 200:
                db_stats = stats_response.json()
                stats.update(db_stats)
            
            return Response({
                'success': True,
                'statistics': stats
            })
            
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return Response({
            'success': False,
            'error': 'Status retrieval failed',
            'message': 'Failed to get processing status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_queue_status(request):
    """Get current queue state"""
    # Verify JWT token
    payload, error = verify_jwt_token(request)
    if error:
        return Response({
            'success': False,
            'error': error,
            'message': 'Authentication failed'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        queue_manager = RedisQueueManager()
        queue_state = queue_manager.get_queue_state()
        
        return Response({
            'success': True,
            'queue': queue_state
        })
        
    except Exception as e:
        logger.error(f"Error getting queue state: {str(e)}")
        return Response({
            'success': False,
            'error': 'Queue retrieval failed',
            'message': 'Failed to get queue state'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def query_rag(request):
    """Query the RAG system"""
    # Verify JWT token
    payload, error = verify_jwt_token(request)
    if error:
        return Response({
            'success': False,
            'error': error,
            'message': 'Authentication failed'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    user_id = payload.get('user_id')
    
    # Get query parameters
    query = request.data.get('query')
    cancer_type_id = request.data.get('cancer_type_id')
    k = request.data.get('k', 5)  # Number of results to return
    
    if not query:
        return Response({
            'success': False,
            'error': 'Missing query',
            'message': 'Query text is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Perform vector search
        results = query_embeddings(query, cancer_type_id, k)
        
        # Log query to database
        requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/rag/queries/log/",
            headers=get_db_headers(),
            json={
                'user_id': user_id,
                'query': query,
                'cancer_type_id': cancer_type_id,
                'results_count': len(results),
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT')
            }
        )
        
        return Response({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error querying RAG: {str(e)}")
        return Response({
            'success': False,
            'error': 'Query failed',
            'message': 'Failed to query the RAG system'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def health_check(request):
    """Health check endpoint"""
    try:
        # Check Redis connection
        queue_manager = RedisQueueManager()
        redis_healthy = queue_manager.health_check()
        
        # Check database service
        db_response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/health/",
            headers=get_db_headers(),
            timeout=5
        )
        db_healthy = db_response.status_code == 200
        
        # Check OpenAI key
        openai_configured = bool(settings.OPENAI_API_KEY)
        
        return Response({
            'status': 'healthy' if (redis_healthy and db_healthy and openai_configured) else 'unhealthy',
            'service': 'rag-embedding-service',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'redis': redis_healthy,
                'database_service': db_healthy,
                'openai_configured': openai_configured
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return Response({
            'status': 'unhealthy',
            'service': 'rag-embedding-service',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)