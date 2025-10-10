"""Service classes for RAG embedding operations"""
import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.cache import cache
from .exceptions import (
    ExternalServiceError, 
    DocumentNotFoundError,
    ProcessingError,
    ValidationError
)
from .utils import RedisQueueManager, query_embeddings
from .langchain_integration import process_rag_query

logger = logging.getLogger(__name__)


class DatabaseService:
    """Handle communication with database service"""
    
    @staticmethod
    def get_headers():
        return {'X-Service-Token': settings.DATABASE_SERVICE_TOKEN}
    
    @classmethod
    def check_document_embeddings(cls, document_id: str) -> bool:
        """Check if document already has embeddings"""
        try:
            response = requests.get(
                f"{settings.DATABASE_SERVICE_URL}/api/rag/documents/{document_id}/has_embeddings/",
                headers=cls.get_headers()
            )
            if response.status_code == 200:
                return response.json().get('has_embeddings', False)
            return False
        except requests.RequestException as e:
            logger.error(f"Failed to check document embeddings: {e}")
            return False
    
    @classmethod
    def create_embedding_job(cls, job_id: str, document_id: str, status: str = 'pending', message: str = '') -> bool:
        """Create embedding job in database"""
        try:
            response = requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/rag/embedding-jobs/create_status/",
                headers=cls.get_headers(),
                json={
                    'job_id': job_id,
                    'document_id': document_id,
                    'status': status,
                    'message': message
                }
            )
            return response.status_code in [200, 201]
        except requests.RequestException as e:
            logger.error(f"Failed to create embedding job: {e}")
            return False
    
    @classmethod
    def log_query(cls, user_id: int, query: str, cancer_type_id: Optional[int], 
                  results_count: int, ip_address: str, user_agent: str, session_id: Optional[str] = None):
        """Log RAG query to database"""
        try:
            requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/rag/queries/log/",
                headers=cls.get_headers(),
                json={
                    'user_id': user_id,
                    'query': query,
                    'cancer_type_id': cancer_type_id,
                    'results_count': results_count,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'session_id': session_id
                }
            )
        except requests.RequestException as e:
            logger.error(f"Failed to log query: {e}")


class EmbeddingService:
    """Handle document embedding operations"""
    
    def __init__(self):
        self.queue_manager = RedisQueueManager()
    
    def process_document(self, document_id: str, cancer_type_id: int, user_id: int, jwt_token: str) -> Dict[str, Any]:
        """Submit document for embedding processing"""
        # Check if already processed
        if DatabaseService.check_document_embeddings(document_id):
            raise ValidationError("Document already has embeddings", 
                                details={'document_id': document_id})
        
        # Create job
        import uuid
        job_id = str(uuid.uuid4())
        
        job_data = {
            'job_id': job_id,
            'document_id': document_id,
            'cancer_type_id': cancer_type_id,
            'user_id': user_id,
            'jwt_token': jwt_token,
            'created_at': datetime.now().isoformat()
        }
        
        # Add to queue
        self.queue_manager.add_job(job_data)
        
        # Create job record
        DatabaseService.create_embedding_job(job_id, document_id, 'pending', 'Job queued for processing')
        
        return {
            'job_id': job_id,
            'document_id': document_id,
            'queue_position': self.queue_manager.get_queue_length()
        }
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get embedding job status"""
        from .utils import get_processing_status
        return get_processing_status(job_id)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = self.queue_manager.get_queue_stats()
        
        # Get additional stats from database
        try:
            response = requests.get(
                f"{settings.DATABASE_SERVICE_URL}/api/rag/embeddings/statistics/",
                headers=DatabaseService.get_headers()
            )
            if response.status_code == 200:
                stats.update(response.json())
        except:
            pass
        
        return stats


class ChatService:
    """Handle chat/query operations"""
    
    @staticmethod
    def get_session_history(session_id: str) -> list:
        """Get chat history from cache"""
        if not session_id:
            return []
        cache_key = f"chat_history_{session_id}"
        return cache.get(cache_key, [])
    
    @staticmethod
    def save_session_history(session_id: str, history: list):
        """Save chat history to cache"""
        if not session_id:
            return
        cache_key = f"chat_history_{session_id}"
        # Keep only last 10 exchanges
        history = history[-10:]
        cache.set(cache_key, history, 3600)  # 1 hour TTL
    
    @classmethod
    def process_query(cls, query: str, cancer_type_id: Optional[int], 
                     session_id: Optional[str], user_id: int,
                     ip_address: str, user_agent: str, language: str) -> Dict[str, Any]:
        """Process a RAG query"""
        # Get session history
        chat_history = cls.get_session_history(session_id)
        
        # Process with LangChain
        result = process_rag_query(
            query=query,
            language=language,
            cancer_type_id=cancer_type_id,
            chat_history=chat_history,
            k=8  # Use more results for better context
        )
        
        if not result['success']:
            # Fallback to raw search
            raw_results = query_embeddings(query, cancer_type_id, 5)
            return {
                'success': True,
                'query': query,
                'results': raw_results,
                'count': len(raw_results),
                'session_id': session_id
            }
        
        # Update session history
        if session_id and result['success']:
            updated_history = chat_history + [(query, result['answer'])]
            cls.save_session_history(session_id, updated_history)
        
        # Log query
        DatabaseService.log_query(
            user_id, query, cancer_type_id, 
            result.get('documents_used', 0),
            ip_address, user_agent, session_id
        )
        
        return {
            'success': True,
            'query': query,
            'answer': result['answer'],
            'sources': result['sources'],
            'results': result.get('raw_results', []),
            'count': len(result.get('raw_results', [])),
            'session_id': session_id
        }
    
    @staticmethod
    def clear_session(session_id: str):
        """Clear session history"""
        if not session_id:
            raise ValidationError("Session ID is required")
        
        cache_key = f"chat_history_{session_id}"
        cache.delete(cache_key)


from datetime import datetime
