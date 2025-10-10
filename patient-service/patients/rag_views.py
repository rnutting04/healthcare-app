"""RAG Chat ViewSet for patient dashboard"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
import logging

from .services import DatabaseService
from .rag_service import RAGService

logger = logging.getLogger(__name__)


class RAGChatViewSet(viewsets.ViewSet):
    """Handle RAG-based chat for patients"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rag_service = RAGService()
    
    @action(detail=False, methods=['post'])
    def query(self, request):
        """
        Process a chat query from the patient
        
        Expected request body:
        {
            "query": "What are the side effects of chemotherapy?"
        }
        """
        # Validate request
        query = request.data.get('query', '').strip()
        if not query:
            return Response(
                {'error': 'Query is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get patient information
        try:
            patient = self._get_patient_info(request)
            if not patient:
                return Response(
                    {'error': 'Patient profile not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Determine cancer type with fallback
            cancer_type = self._get_cancer_type(patient)
            
            # Get auth token
            auth_token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
            if not auth_token:
                return Response(
                    {'error': 'Authentication required'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get session ID from request or generate new one
            session_id = request.data.get('session_id')
            
            # Query RAG service with session support
            try:
                result = self.rag_service.query_with_context(
                    query=query,
                    cancer_type=cancer_type,
                    auth_token=auth_token,
                    session_id=session_id
                )
                logger.info(f"RAG service returned: type={type(result)}, value={result}")
            except Exception as rag_error:
                logger.error(f"Exception calling RAG service: {rag_error}")
                result = {
                    'success': False,
                    'error': str(rag_error),
                    'response': 'I apologize, but I encountered an error processing your request.'
                }
            
            # Ensure result is always a dict
            if not isinstance(result, dict):
                logger.error(f"RAG service returned non-dict result: {type(result)} - {result}")
                result = {
                    'success': False,
                    'error': 'Invalid response from RAG service',
                    'response': 'I apologize, but I encountered an error processing your request.'
                }
            
            # Log the interaction
            self._log_chat_interaction(request.user_id, query, cancer_type)
            
            # Format response based on RAG service response structure
            logger.info(f"About to check result.get('success'), result type: {type(result)}, value: {result}")
            if result.get('success'):
                # Check if we have a LangChain-generated answer
                if 'answer' in result:
                    # Use the LangChain-generated answer
                    response_text = result.get('answer', '')
                    sources = result.get('sources', [])
                    
                    response_data = {
                        'query': query,
                        'response': response_text,
                        'cancer_type_context': cancer_type,
                        'timestamp': timezone.now().isoformat(),
                        'sources': sources if (sources and isinstance(sources[0], str)) else [s.get('filename', 'Unknown source') for s in sources[:3] if isinstance(s, dict)],
                        'session_id': result.get('session_id', session_id)
                    }
                else:
                    # Fallback to raw results processing
                    # Extract text from results and format as a response
                    results = result.get('results', [])
                    if results:
                        # Log the structure of results for debugging
                        logger.info(f"Results structure - type: {type(results)}, length: {len(results)}")
                        if results:
                            logger.info(f"First result type: {type(results[0])}")
                            if isinstance(results[0], dict):
                                logger.info(f"First result keys: {list(results[0].keys())}")
                        
                        # Combine relevant chunks into a response
                        response_text = self._format_rag_response(results)
                        
                        # Extract sources - check if results contain dicts
                        sources = []
                        for r in results[:3]:
                            if isinstance(r, dict):
                                metadata = r.get('metadata', {})
                                if isinstance(metadata, dict):
                                    sources.append(metadata.get('filename', 'Unknown source'))
                                else:
                                    sources.append('Unknown source')
                            else:
                                sources.append('Unknown source')
                    else:
                        response_text = "I couldn't find relevant information to answer your question."
                        sources = []
                    
                    response_data = {
                        'query': query,
                        'response': response_text,
                        'cancer_type_context': cancer_type,
                        'timestamp': timezone.now().isoformat(),
                        'sources': sources,
                        'session_id': result.get('session_id', session_id)
                    }
            else:
                # Error response
                response_data = {
                    'query': query,
                    'response': result.get('response', 'I apologize, but I could not process your query.'),
                    'cancer_type_context': cancer_type,
                    'timestamp': timezone.now().isoformat(),
                    'sources': []
                }
                if 'error' in result:
                    response_data['error'] = result['error']
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            logger.error(f"Error processing RAG query: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {
                    'error': 'An error occurred processing your query',
                    'response': 'I apologize, but I encountered an error. Please try again later.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def clear_session(self, request):
        """Clear chat session history"""
        session_id = request.data.get('session_id')
        if not session_id:
            return Response(
                {'error': 'Session ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get auth token
        auth_token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
        if not auth_token:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            result = self.rag_service.clear_session(
                session_id=session_id,
                auth_token=auth_token
            )
            
            if result.get('success'):
                return Response({
                    'success': True,
                    'message': 'Chat history cleared',
                    'session_id': session_id
                })
            else:
                return Response(
                    {'error': result.get('error', 'Failed to clear session')}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error clearing session: {str(e)}")
            return Response(
                {'error': 'Failed to clear session'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def context(self, request):
        """Get the current cancer type context for the patient"""
        try:
            patient = self._get_patient_info(request)
            if not patient:
                return Response(
                    {'error': 'Patient profile not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            cancer_type = self._get_cancer_type(patient)
            
            preferred_language = patient.get('preferred_language', 'English')
            
            return Response({
                'cancer_type': cancer_type,
                'language': preferred_language,
                'is_fallback': cancer_type == 'uterine' and not self._patient_has_uterine_cancer(patient)
            })
            
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return Response(
                {'error': 'Unable to determine context'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_patient_info(self, request) -> dict:
        """Get patient information from database service"""
        if not hasattr(request, 'user_id'):
            return None
        
        return DatabaseService.get_patient_by_user_id(request.user_id)
    
    def _get_cancer_type(self, patient: dict) -> str:
        """Extract cancer type from patient data with fallback"""
        # Try to get cancer type from patient profile
        cancer_type = patient.get('cancer_type', '').strip()
        
        if not cancer_type:
            # Try to get from cancer_type_detail
            cancer_detail = patient.get('cancer_type_detail', {})
            if isinstance(cancer_detail, dict):
                cancer_type = cancer_detail.get('name', '').strip()
        
        # Default to uterine if not found or empty
        if not cancer_type:
            logger.info(f"No cancer type found for patient {patient.get('id')}, using fallback")
            cancer_type = 'uterine'
        
        return cancer_type.lower()
    
    def _patient_has_uterine_cancer(self, patient: dict) -> bool:
        """Check if patient actually has uterine cancer"""
        cancer_type = self._get_cancer_type(patient)
        return 'uterine' in cancer_type or 'endometrial' in cancer_type
    
    def _log_chat_interaction(self, user_id: int, query: str, cancer_type: str):
        """Log chat interaction for analytics"""
        try:
            DatabaseService.log_event(
                event_type='rag_chat_query',
                service='patient-service',
                data={
                    'user_id': user_id,
                    'query': query[:200],  # Limit query length for logging
                    'cancer_type_context': cancer_type,
                    'timestamp': timezone.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to log chat interaction: {e}")
    
    def _format_rag_response(self, results: list) -> str:
        """Format RAG search results into a coherent response"""
        if not results:
            return "I couldn't find relevant information to answer your question."
        
        # Get unique chunks of text
        seen_texts = set()
        relevant_chunks = []
        
        for result in results[:5]:  # Use top 5 results
            if isinstance(result, dict):
                text = result.get('chunk_text', '').strip()
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    relevant_chunks.append(text)
            elif isinstance(result, str):
                # If result is just a string, use it directly
                text = result.strip()
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    relevant_chunks.append(text)
        
        if not relevant_chunks:
            return "I found some documents but couldn't extract relevant information."
        
        # Combine chunks into a response
        response = "Based on the medical documents, here's what I found:\n\n"
        response += "\n\n".join(relevant_chunks[:3])  # Limit to 3 chunks
        
        return response
