"""Document processing logic for embeddings"""
import os
import logging
import requests
from typing import Dict, Any, Callable, Optional
from django.conf import settings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

from .exceptions import ProcessingError, ExternalServiceError

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handle document processing and embedding generation"""
    
    def __init__(self):
        self.embeddings_model = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def process_job(self, job_data: Dict[str, Any], 
                   progress_callback: Callable[[str, str, str, Optional[dict]], None]):
        """Process a single embedding job"""
        job_id = job_data['job_id']
        document_id = job_data['document_id']
        cancer_type_id = job_data['cancer_type_id']
        jwt_token = job_data['jwt_token']
        
        logger.info(f"Processing job {job_id} for document {document_id}")
        
        # Download and process file
        temp_file_path = None
        try:
            # Download file
            temp_file_path = self._download_file(document_id, jwt_token)
            
            # Get filename
            filename = self._get_filename(document_id)
            
            # Load and split document
            chunks = self._load_and_split_document(
                temp_file_path, filename, job_id, progress_callback
            )
            
            # Generate embeddings and save
            self._process_chunks(
                chunks, document_id, cancer_type_id, 
                filename, job_id, progress_callback
            )
            
            # Final update
            progress_callback(job_id, 'completed', 
                            f'Successfully processed {len(chunks)} chunks',
                            {
                                'phase': 'completed',
                                'total_chunks': len(chunks),
                                'processed_chunks': len(chunks),
                                'percentage': 100
                            })
            
        finally:
            # Cleanup
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def _download_file(self, document_id: str, jwt_token: str) -> str:
        """Download file from file service"""
        headers = {'Authorization': f'Bearer {jwt_token}'}
        
        response = requests.get(
            f"{settings.FILE_SERVICE_URL}/api/files/{document_id}",
            headers=headers,
            stream=True
        )
        
        if response.status_code != 200:
            raise ExternalServiceError(
                f"Failed to download file: {response.status_code}",
                details={'document_id': document_id, 'status': response.status_code}
            )
        
        # Save to temp file
        temp_file_path = os.path.join(settings.TEMP_FILE_PATH, f"{document_id}.pdf")
        with open(temp_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return temp_file_path
    
    def _get_filename(self, document_id: str) -> str:
        """Get filename from database service"""
        try:
            headers = {'X-Service-Token': settings.DATABASE_SERVICE_TOKEN}
            response = requests.get(
                f"{settings.DATABASE_SERVICE_URL}/api/files/{document_id}/",
                headers=headers
            )
            if response.status_code == 200:
                return response.json().get('filename', 'unknown.pdf')
        except:
            pass
        return 'unknown.pdf'
    
    def _load_and_split_document(self, file_path: str, filename: str, 
                                job_id: str, progress_callback: Callable) -> list:
        """Load PDF and split into chunks"""
        # Update progress
        progress_callback(job_id, 'processing', 'Loading document', {
            'phase': 'loading',
            'total_chunks': 0,
            'processed_chunks': 0,
            'percentage': 0
        })
        
        # Load document
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # Add filename to metadata
        for doc in documents:
            doc.metadata['filename'] = filename
            doc.metadata['source'] = filename
        
        # Update progress
        progress_callback(job_id, 'processing', 'Splitting document into chunks', {
            'phase': 'splitting',
            'total_chunks': 0,
            'processed_chunks': 0,
            'percentage': 10
        })
        
        # Split documents
        chunks = self.text_splitter.split_documents(documents)
        
        logger.info(f"Split document into {len(chunks)} chunks")
        return chunks
    
    def _process_chunks(self, chunks: list, document_id: str, 
                       cancer_type_id: int, filename: str,
                       job_id: str, progress_callback: Callable):
        """Process chunks and save embeddings"""
        # Update progress
        progress_callback(job_id, 'processing', 
                         f'Generating embeddings for {len(chunks)} chunks', {
                             'phase': 'embedding',
                             'total_chunks': len(chunks),
                             'processed_chunks': 0,
                             'percentage': 20
                         })
        
        # Process chunks
        chunk_data = []
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = self.embeddings_model.embed_query(chunk.page_content)
            
            chunk_data.append({
                'document_id': document_id,
                'cancer_type_id': cancer_type_id,
                'chunk_index': i,
                'chunk_text': chunk.page_content,
                'embedding': embedding,
                'metadata': {
                    'page': chunk.metadata.get('page', 0),
                    'source': chunk.metadata.get('source', ''),
                    'filename': filename,
                    'job_id': job_id
                }
            })
            
            # Update progress for every 10 chunks or last chunk
            if (i + 1) % 10 == 0 or i == len(chunks) - 1:
                progress_percentage = 20 + int(((i + 1) / len(chunks)) * 60)
                progress_callback(
                    job_id, 'processing',
                    f'Processing chunk {i + 1} of {len(chunks)}',
                    {
                        'phase': 'embedding',
                        'total_chunks': len(chunks),
                        'processed_chunks': i + 1,
                        'percentage': progress_percentage
                    }
                )
        
        # Save to database
        progress_callback(job_id, 'processing', 'Saving embeddings to database', {
            'phase': 'saving',
            'total_chunks': len(chunks),
            'processed_chunks': len(chunks),
            'percentage': 90
        })
        
        self._save_embeddings(document_id, chunk_data)
    
    def _save_embeddings(self, document_id: str, chunk_data: list):
        """Save embeddings to database via database service"""
        headers = {'X-Service-Token': settings.DATABASE_SERVICE_TOKEN}
        
        response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/rag/embeddings/bulk_create/",
            headers=headers,
            json={
                'document_id': document_id,
                'chunks': chunk_data
            }
        )
        
        if response.status_code != 201:
            raise ExternalServiceError(
                f"Failed to save embeddings: {response.text}",
                details={'status': response.status_code}
            )
        
        logger.info(f"Successfully saved {len(chunk_data)} embeddings")