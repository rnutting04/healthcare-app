import requests
import logging
from typing import List, Dict, Optional, Any
from django.conf import settings
import json

logger = logging.getLogger('embedding')


class DatabaseClient:
    """Client for communicating with the database service."""
    
    def __init__(self):
        self.base_url = settings.DATABASE_SERVICE_URL
        self.headers = {
            'X-Service-Token': 'db-service-secret-token',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make a request to the database service."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making {method} request to {url}")
            if method == 'GET':
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code in [200, 201]:
                return response.json() if response.content else {}
            else:
                logger.error(f"Database service error: {response.status_code} for {url} - {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Database service request failed: {str(e)}")
            return None
    
    def check_embedding_exists(self, document_id: str) -> bool:
        """Check if embeddings already exist for a document."""
        result = self._make_request('GET', f'/api/embeddings/exists/{document_id}/')
        return result.get('exists', False) if result else False
    
    def check_hash_exists(self, file_hash: str) -> bool:
        """Check if a file with the same hash already exists."""
        result = self._make_request('POST', '/api/embeddings/check-hash/', {'file_hash': file_hash})
        return result.get('exists', False) if result else False
    
    def store_embeddings(self, document_id: str, file_hash: str, embeddings: List[Optional[List[float]]],
                        text_chunks: List[str], user_id: str, metadata: Dict[str, Any]) -> bool:
        """Store embeddings in the database."""
        # Prepare embedding data
        embedding_data = []
        for i, (embedding, chunk) in enumerate(zip(embeddings, text_chunks)):
            if embedding is not None:
                embedding_data.append({
                    'chunk_index': i,
                    'chunk_text': chunk,  # Store full chunk text for RAG
                    'embedding_vector': json.dumps(embedding),  # Store as JSON string
                    'vector_dimension': len(embedding)
                })
        
        if not embedding_data:
            logger.error("No valid embeddings to store")
            return False
        
        # Add metadata about the file
        if 'filename' not in metadata:
            metadata['filename'] = f"document_{document_id}"
        if 'file_size' not in metadata:
            metadata['file_size'] = 0
        if 'storage_path' not in metadata:
            metadata['storage_path'] = f"embeddings/{document_id}"
        
        data = {
            'document_id': document_id,
            'file_hash': file_hash,
            'user_id': user_id,
            'embeddings': embedding_data,
            'metadata': metadata
        }
        
        result = self._make_request('POST', '/api/embeddings/store/', data)
        return result is not None
    
    def get_embeddings(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve embeddings for a document."""
        return self._make_request('GET', f'/api/embeddings/{document_id}/')
    
    def search_similar_documents(self, query_embedding: List[float], top_k: int = 5,
                                threshold: float = 0.7) -> Optional[List[Dict[str, Any]]]:
        """Search for similar documents based on embedding similarity."""
        data = {
            'query_embedding': query_embedding,
            'top_k': top_k,
            'threshold': threshold
        }
        
        result = self._make_request('POST', '/api/embeddings/search/', data)
        return result.get('results', []) if result else None
    
    def delete_embeddings(self, document_id: str) -> bool:
        """Delete embeddings for a document."""
        result = self._make_request('DELETE', f'/api/embeddings/{document_id}/')
        return result is not None
    
    def get_user_embeddings(self, user_id: str, page: int = 1, limit: int = 20) -> Optional[Dict[str, Any]]:
        """Get all embeddings for a specific user."""
        result = self._make_request('GET', f'/api/embeddings/user/{user_id}/?page={page}&limit={limit}')
        return result
    
    def update_embedding_metadata(self, document_id: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for an embedding."""
        data = {'metadata': metadata}
        result = self._make_request('PUT', f'/api/embeddings/{document_id}/metadata/', data)
        return result is not None