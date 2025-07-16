from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.conf import settings
import os
import logging
import tempfile
from datetime import datetime
from utils.queue_manager import queue_manager
from utils.embedding_generator import EmbeddingGenerator
from utils.database_client import DatabaseClient

logger = logging.getLogger('embedding')


class ProcessEmbeddingView(APIView):
    """Submit a file for embedding processing."""
    
    def post(self, request):
        try:
            # Get file from request
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get document ID and metadata
            document_id = request.data.get('document_id')
            if not document_id:
                return Response({'error': 'Document ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file type
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            if file_extension not in settings.ALLOWED_FILE_TYPES:
                return Response({
                    'error': f'File type {file_extension} not allowed. Allowed types: {", ".join(settings.ALLOWED_FILE_TYPES)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file size
            if uploaded_file.size > settings.MAX_FILE_SIZE:
                return Response({
                    'error': f'File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save file temporarily
            temp_dir = settings.TEMP_FILE_PATH
            os.makedirs(temp_dir, exist_ok=True)
            
            temp_file_path = os.path.join(temp_dir, f"{document_id}_{uploaded_file.name}")
            with open(temp_file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            
            # Add task to queue
            user_id = getattr(request, 'user_id', 'unknown')
            priority = int(request.data.get('priority', 0))
            
            task = queue_manager.add_task(
                document_id=document_id,
                file_path=temp_file_path,
                file_type=file_extension,
                user_id=user_id,
                priority=priority
            )
            
            # Check if task was rejected as duplicate
            if task.status == 'duplicate':
                # Clean up the temp file
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
                return Response({
                    'error': task.error,
                    'status': 'duplicate'
                }, status=status.HTTP_409_CONFLICT)
            
            return Response({
                'message': 'File submitted for embedding processing',
                'document_id': document_id,
                'queue_position': queue_manager.queue.qsize(),
                'status': task.to_dict()
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Error processing embedding request: {str(e)}")
            return Response({
                'error': 'Failed to process embedding request'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmbeddingStatusView(APIView):
    """Get overall queue status and statistics."""
    
    def get(self, request):
        try:
            status_data = queue_manager.get_queue_status()
            
            return Response({
                'status': 'operational',
                'queue': status_data,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting queue status: {str(e)}")
            return Response({
                'error': 'Failed to get queue status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentEmbeddingStatusView(APIView):
    """Get specific document processing status."""
    
    def get(self, request, document_id):
        try:
            task_status = queue_manager.get_task_status(document_id)
            
            if not task_status:
                # Check if embeddings exist in database
                db_client = DatabaseClient()
                if db_client.check_embedding_exists(document_id):
                    return Response({
                        'status': 'completed',
                        'message': 'Embeddings exist in database',
                        'document_id': document_id
                    })
                else:
                    return Response({
                        'error': 'Document not found in queue or database'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            return Response(task_status)
            
        except Exception as e:
            logger.error(f"Error getting document status: {str(e)}")
            return Response({
                'error': 'Failed to get document status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QueueView(APIView):
    """View current queue state."""
    
    def get(self, request):
        try:
            queue_items = queue_manager.get_queue_items()
            
            return Response({
                'queue_items': queue_items,
                'total_items': len(queue_items),
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting queue items: {str(e)}")
            return Response({
                'error': 'Failed to get queue items'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SearchSimilarView(APIView):
    """Search for similar documents based on text query."""
    
    def post(self, request):
        try:
            query_text = request.data.get('query')
            if not query_text:
                return Response({'error': 'Query text is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            top_k = int(request.data.get('top_k', 5))
            threshold = float(request.data.get('threshold', 0.7))
            
            # Generate embedding for query
            embedding_generator = EmbeddingGenerator()
            query_embedding = embedding_generator.generate_embedding(query_text)
            
            if not query_embedding:
                return Response({
                    'error': 'Failed to generate embedding for query'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Search for similar documents
            db_client = DatabaseClient()
            results = db_client.search_similar_documents(query_embedding, top_k, threshold)
            
            if results is None:
                return Response({
                    'error': 'Failed to search for similar documents'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'query': query_text,
                'results': results,
                'count': len(results)
            })
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {str(e)}")
            return Response({
                'error': 'Failed to search for similar documents'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserEmbeddingsView(APIView):
    """Get all embeddings for the authenticated user."""
    
    def get(self, request):
        try:
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return Response({'error': 'User ID not found'}, status=status.HTTP_401_UNAUTHORIZED)
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            db_client = DatabaseClient()
            result = db_client.get_user_embeddings(user_id, page, limit)
            
            if result is None:
                return Response({
                    'error': 'Failed to retrieve user embeddings'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error getting user embeddings: {str(e)}")
            return Response({
                'error': 'Failed to get user embeddings'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)