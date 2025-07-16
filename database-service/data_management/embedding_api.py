from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import DocumentEmbedding, EmbeddingChunk, FileMetadata
import json


@api_view(['GET'])
def check_embedding_exists(request, document_id):
    """Check if embeddings already exist for a document."""
    exists = DocumentEmbedding.objects.filter(file_id=document_id).exists()
    return Response({'exists': exists})


@api_view(['POST'])
def check_hash_exists(request):
    """Check if a file with the same hash already exists."""
    file_hash = request.data.get('file_hash')
    if not file_hash:
        return Response({'error': 'file_hash is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if embeddings already exist for this file hash
    exists = DocumentEmbedding.objects.filter(file_hash=file_hash).exists()
    return Response({'exists': exists})


@api_view(['POST'])
def store_embeddings(request):
    """Store embeddings in the database."""
    document_id = request.data.get('document_id')
    file_hash = request.data.get('file_hash')
    user_id = request.data.get('user_id')
    embeddings = request.data.get('embeddings', [])
    metadata = request.data.get('metadata', {})
    
    if not all([document_id, file_hash, user_id, embeddings]):
        return Response({
            'error': 'document_id, file_hash, user_id, and embeddings are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get or create file metadata
        file_metadata, created = FileMetadata.objects.get_or_create(
            id=document_id,
            defaults={
                'user_id': user_id,
                'filename': metadata.get('filename', 'unknown'),
                'file_hash': file_hash,
                'file_size': metadata.get('file_size', 0),
                'mime_type': metadata.get('file_type', 'application/octet-stream'),
                'storage_path': metadata.get('storage_path', ''),
                'is_encrypted': False
            }
        )
        
        # Create or update document embedding
        doc_embedding, created = DocumentEmbedding.objects.update_or_create(
            file=file_metadata,
            defaults={
                'total_chunks': len(embeddings),
                'embedding_model': metadata.get('model', 'text-embedding-ada-002'),
                'processing_status': 'completed',
                'processed_at': timezone.now()
            }
        )
        
        # Store embedding chunks
        for embedding_data in embeddings:
            EmbeddingChunk.objects.create(
                document_embedding=doc_embedding,
                chunk_index=embedding_data['chunk_index'],
                chunk_text_preview=embedding_data['chunk_text'][:500],
                embedding_vector=embedding_data['embedding_vector'],
                vector_dimension=embedding_data['vector_dimension']
            )
        
        return Response({'success': True, 'document_id': str(file_metadata.id)})
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_embeddings(request, document_id):
    """Retrieve embeddings for a document."""
    try:
        doc_embedding = DocumentEmbedding.objects.select_related('file').prefetch_related('chunks').get(
            file_id=document_id
        )
        
        chunks = [{
            'chunk_index': chunk.chunk_index,
            'chunk_text_preview': chunk.chunk_text_preview,
            'embedding_vector': json.loads(chunk.embedding_vector),
            'vector_dimension': chunk.vector_dimension
        } for chunk in doc_embedding.chunks.all().order_by('chunk_index')]
        
        return Response({
            'document_id': str(doc_embedding.file.id),
            'total_chunks': doc_embedding.total_chunks,
            'embedding_model': doc_embedding.embedding_model,
            'processing_status': doc_embedding.processing_status,
            'chunks': chunks
        })
        
    except DocumentEmbedding.DoesNotExist:
        return Response({'error': 'Embeddings not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def search_similar_documents(request):
    """Search for similar documents based on embedding similarity."""
    query_embedding = request.data.get('query_embedding')
    top_k = request.data.get('top_k', 5)
    threshold = request.data.get('threshold', 0.7)
    
    if not query_embedding:
        return Response({'error': 'query_embedding is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # This is a simplified implementation
    # In production, you would use a vector database or PostgreSQL with pgvector
    results = []
    
    # For now, return empty results
    # A real implementation would calculate cosine similarity between query_embedding
    # and all stored embeddings, then return the top-k most similar documents
    
    return Response({
        'results': results,
        'query_dimension': len(query_embedding) if isinstance(query_embedding, list) else 0,
        'top_k': top_k,
        'threshold': threshold
    })


@api_view(['DELETE'])
def delete_embeddings(request, document_id):
    """Delete embeddings for a document."""
    try:
        # Delete chunks first (due to foreign key constraint)
        EmbeddingChunk.objects.filter(document_embedding__file_id=document_id).delete()
        
        # Delete document embedding
        DocumentEmbedding.objects.filter(file_id=document_id).delete()
        
        return Response({'success': True, 'message': 'Embeddings deleted successfully'})
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_user_embeddings(request, user_id):
    """Get all embeddings for a specific user."""
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    offset = (page - 1) * limit
    
    embeddings = DocumentEmbedding.objects.filter(
        file__user_id=user_id
    ).select_related('file').order_by('-file__uploaded_at')[offset:offset + limit]
    
    total = DocumentEmbedding.objects.filter(file__user_id=user_id).count()
    
    data = [{
        'document_id': str(emb.file.id),
        'filename': emb.file.filename,
        'total_chunks': emb.total_chunks,
        'embedding_model': emb.embedding_model,
        'processing_status': emb.processing_status,
        'processed_at': emb.processed_at
    } for emb in embeddings]
    
    return Response({
        'embeddings': data,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': (total + limit - 1) // limit
        }
    })


@api_view(['PUT'])
def update_embedding_metadata(request, document_id):
    """Update metadata for an embedding."""
    metadata = request.data.get('metadata')
    if not metadata:
        return Response({'error': 'metadata is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        doc_embedding = DocumentEmbedding.objects.get(file_id=document_id)
        
        # Update specific fields if provided
        if 'processing_status' in metadata:
            doc_embedding.processing_status = metadata['processing_status']
        if 'error_message' in metadata:
            doc_embedding.error_message = metadata['error_message']
        if 'total_chunks' in metadata:
            doc_embedding.total_chunks = metadata['total_chunks']
            
        doc_embedding.save()
        
        return Response({'success': True})
        
    except DocumentEmbedding.DoesNotExist:
        return Response({'error': 'Embedding not found'}, status=status.HTTP_404_NOT_FOUND)