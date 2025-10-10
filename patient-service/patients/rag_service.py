"""RAG Service for patient chat functionality"""
import logging
from typing import Dict, Any, Optional, List
import requests
from django.conf import settings
import uuid

logger = logging.getLogger(__name__)


class RAGService:
    """Handle RAG-based chat queries for patients"""
    
    BASE_URL = None
    TIMEOUT = 30
    FALLBACK_CANCER_TYPE = 'uterine'
    
    def __init__(self):
        self.base_url = getattr(settings, 'RAG_EMBEDDING_SERVICE_URL', 'http://rag-embedding-service:8007')
        self.sessions = {}  # In-memory session storage (consider Redis for production)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to RAG service with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Set default headers
        headers = kwargs.get('headers', {})
        headers['Content-Type'] = 'application/json'
        kwargs['headers'] = headers
        
        # Set timeout
        kwargs['timeout'] = kwargs.get('timeout', self.TIMEOUT)
        
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Parse JSON response
            try:
                return response.json()
            except ValueError as json_error:
                logger.error(f"Failed to parse JSON response: {json_error}")
                return {
                    'success': False,
                    'error': 'Invalid JSON response',
                    'response': 'Unable to parse response from knowledge base service.'
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"RAG service request failed: {method} {url} - {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Unable to connect to the knowledge base service.'
            }
    
    def query_with_context(self, query: str, cancer_type: str, auth_token: str, 
                          session_id: Optional[str] = None, 
                          chat_history: Optional[List] = None, language: str = 'English') -> Dict[str, Any]:
        """
        Query RAG system with patient's cancer type context and session support
        
        Args:
            query: The user's question
            cancer_type: Patient's cancer type for context
            auth_token: JWT token for authentication
            session_id: Optional session ID for conversation tracking
            chat_history: Optional chat history for context
            
        Returns:
            Dict containing the RAG response
        """
        headers = {'Authorization': f'Bearer {auth_token}'}
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # For now, we'll pass None as cancer_type_id to get all results
        # In production, you'd want to map cancer type names to IDs

        data = {
            'query': query,
            'language': language,
            'cancer_type_id': None,  # Will search across all cancer types
            'session_id': session_id,
            'chat_history': chat_history or [],
            'k': 8  # Get more results for better context
        }
        
        # Try with patient's specific cancer type
        result = self._make_request(
            'POST', 
            '/api/rag/chat/query/', 
            json=data, 
            headers=headers
        )
        
        # If the first request failed, try fallback
        if not result.get('success') and cancer_type.lower() != self.FALLBACK_CANCER_TYPE:
            logger.warning(
                f"RAG query failed for cancer type '{cancer_type}', "
                f"falling back to '{self.FALLBACK_CANCER_TYPE}'"
            )
            data['cancer_type_id'] = None  # Search all types as fallback
            result = self._make_request(
                'POST', 
                '/api/rag/chat/query/', 
                json=data, 
                headers=headers
            )
        
        # Add session_id to result
        if result.get('success'):
            result['session_id'] = session_id
        
        return result
    
    def clear_session(self, session_id: str, auth_token: str) -> Dict[str, Any]:
        """
        Clear chat session history
        
        Args:
            session_id: Session ID to clear
            auth_token: JWT token for authentication
            
        Returns:
            Dict containing the result
        """
        headers = {'Authorization': f'Bearer {auth_token}'}
        data = {'session_id': session_id}
        
        result = self._make_request(
            'POST',
            '/api/rag/chat/clear-session/',
            json=data,
            headers=headers
        )
        
        return result
