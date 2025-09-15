"""Utility functions for RAG embedding service"""
import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from django.conf import settings
from langchain_openai import OpenAIEmbeddings

from .exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

# Re-export queue manager for compatibility
from .queue_manager import RedisQueueManager


def query_embeddings(query: str, cancer_type_id: Optional[int] = None, k: int = 5) -> List[Dict[str, Any]]:
    """Query embeddings using vector similarity search"""
    try:
        # Generate query embedding
        embeddings_model = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        query_embedding = embeddings_model.embed_query(query)
        
        # Search via database service
        headers = {'X-Service-Token': settings.DATABASE_SERVICE_TOKEN}
        response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/rag/embeddings/search/",
            headers=headers,
            json={
                'query_embedding': query_embedding,
                'cancer_type_id': cancer_type_id,
                'k': k
            }
        )
        
        if response.status_code == 200:
            return response.json()['results']
        else:
            logger.error(f"Search failed: {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error querying embeddings: {str(e)}")
        return []


def get_processing_status(job_id: str) -> Dict[str, Any]:
    """Get processing status for a job"""
    queue_manager = RedisQueueManager()
    
    # Check Redis first
    status_key = f"{queue_manager.status_key_prefix}{job_id}"
    job_data = queue_manager.redis_client.get(status_key)
    
    if job_data:
        return json.loads(job_data)
    
    # Check database as fallback
    try:
        headers = {'X-Service-Token': settings.DATABASE_SERVICE_TOKEN}
        response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/rag/embeddings/status/{job_id}/",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'status': 'unknown',
                'message': 'Job not found'
            }
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }


def cleanup_temp_file(file_path: str):
    """Clean up temporary file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {file_path}: {str(e)}")


# Legacy function for backward compatibility
def process_document_for_embedding(file_path: str, document_id: str, cancer_type_id: int) -> int:
    """
    Process a document and create embeddings (synchronous version)
    This is kept for backward compatibility but should not be used
    """
    logger.warning("Using deprecated process_document_for_embedding function")
    
    from .document_processor import DocumentProcessor
    processor = DocumentProcessor()
    
    # Simple progress callback that does nothing
    def noop_progress(job_id, status, message, progress=None):
        pass
    
    # Create a fake job data structure
    job_data = {
        'job_id': 'sync-job',
        'document_id': document_id,
        'cancer_type_id': cancer_type_id,
        'jwt_token': ''  # No JWT in sync mode
    }
    
    try:
        processor.process_job(job_data, noop_progress)
        return 1  # Return success
    except Exception as e:
        logger.error(f"Error in sync document processing: {e}")
        raise