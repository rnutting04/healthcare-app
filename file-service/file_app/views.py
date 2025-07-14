import os
import uuid
import requests
import logging
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils import (
    calculate_file_hash,
    encrypt_file,
    decrypt_file,
    save_encrypted_file,
    read_encrypted_file,
    delete_file
)
import jwt
from datetime import datetime
import mimetypes

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
        'X-Service-Token': getattr(settings, 'DATABASE_SERVICE_TOKEN', 'db-service-secret-token')
    }


def get_user_encryption_key(user_id):
    """Get or create user encryption key from database service"""
    try:
        response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/encryption-keys/get_or_create_key/",
            params={'user_id': user_id},
            headers=get_db_headers()
        )
        if response.status_code == 200:
            return response.json()['key']
        else:
            logger.error(f"Failed to get encryption key: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting encryption key: {str(e)}")
        return None


@api_view(['POST'])
@csrf_exempt
def upload_file(request):
    """Handle file upload with deduplication and encryption"""
    # Verify JWT token
    payload, error = verify_jwt_token(request)
    if error:
        return Response({
            'success': False,
            'error': error,
            'message': 'Authentication failed'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    user_id = payload.get('user_id')
    
    # Check if file was provided
    if 'file' not in request.FILES:
        return Response({
            'success': False,
            'error': 'No file provided',
            'message': 'Please select a file to upload'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    uploaded_file = request.FILES['file']
    
    # Check file size
    if uploaded_file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        return Response({
            'success': False,
            'error': 'File too large',
            'message': f'File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Calculate file hash
        uploaded_file.seek(0)  # Reset file pointer
        file_hash = calculate_file_hash(uploaded_file)
        
        # Check for duplicate in database
        response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/check_duplicate/",
            json={'file_hash': file_hash},
            headers=get_db_headers()
        )
        
        if response.status_code == 200 and response.json()['exists']:
            return Response({
                'success': False,
                'error': 'Duplicate file',
                'message': 'This file already exists in the system',
                'file_hash': file_hash
            }, status=status.HTTP_409_CONFLICT)
        
        # Get user encryption key
        encryption_key = get_user_encryption_key(user_id)
        if not encryption_key:
            return Response({
                'success': False,
                'error': 'Encryption key error',
                'message': 'Failed to retrieve encryption key'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Encrypt file
        uploaded_file.seek(0)  # Reset file pointer
        encrypted_data = encrypt_file(uploaded_file, encryption_key)
        
        # Generate unique storage path
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(uploaded_file.name)[1]
        storage_filename = f"{file_id}{file_extension}"
        storage_path = os.path.join(settings.FILE_STORAGE_PATH, str(user_id), storage_filename)
        
        # Save encrypted file
        save_encrypted_file(encrypted_data, storage_path)
        
        # Store metadata in database
        metadata_payload = {
            'user_id': user_id,
            'filename': uploaded_file.name,
            'file_hash': file_hash,
            'file_size': uploaded_file.size,
            'mime_type': uploaded_file.content_type or 'application/octet-stream',
            'storage_path': storage_path,
            'is_encrypted': True,
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT')
        }
        
        # logger.info(f"Sending metadata to database service: {metadata_payload}")
        # logger.info(f"Database URL: {settings.DATABASE_SERVICE_URL}/api/files/create_metadata/")
        # logger.info(f"Headers: {get_db_headers()}")
        
        metadata_response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/create_metadata/",
            headers=get_db_headers(),
            json=metadata_payload
        )
        
        # logger.info(f"Metadata creation response: {metadata_response.status_code}")
        # logger.info(f"Response content: {metadata_response.text}")
        
        if metadata_response.status_code == 201:
            file_data = metadata_response.json()
            return Response({
                'success': True,
                'message': 'File uploaded successfully',
                'file_id': file_data['id'],
                'filename': file_data['filename'],
                'uploaded_at': file_data['uploaded_at'],
                'size': uploaded_file.size,
                'mime_type': uploaded_file.content_type
            }, status=status.HTTP_201_CREATED)
        else:
            # Clean up file if metadata creation fails
            delete_file(storage_path)
            return Response({
                'success': False,
                'error': 'Metadata creation failed',
                'message': 'Failed to save file metadata'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Upload failed',
            'message': 'An error occurred during file upload'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def download_file(request, file_id):
    """Download and decrypt a file"""
    # Verify JWT token
    payload, error = verify_jwt_token(request)
    if error:
        return Response({
            'success': False,
            'error': error,
            'message': 'Authentication failed'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    user_id = payload.get('user_id')
    
    try:
        # Get file metadata from database
        response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/",
            headers=get_db_headers()
        )
        
        if response.status_code != 200:
            return Response({
                'success': False,
                'error': 'File not found',
                'message': 'The requested file does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        file_metadata = response.json()
        
        # Check if user owns the file
        if str(file_metadata['user']) != str(user_id):
            return Response({
                'success': False,
                'error': 'Unauthorized',
                'message': 'You do not have permission to access this file'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if file is deleted
        if file_metadata.get('is_deleted'):
            return Response({
                'success': False,
                'error': 'File deleted',
                'message': 'This file has been deleted'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get user encryption key
        encryption_key = get_user_encryption_key(user_id)
        if not encryption_key:
            return Response({
                'success': False,
                'error': 'Encryption key error',
                'message': 'Failed to retrieve encryption key'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Read and decrypt file
        encrypted_data = read_encrypted_file(file_metadata['storage_path'])
        decrypted_data = decrypt_file(encrypted_data, encryption_key)
        
        # Log file access
        requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/log_access/",
            headers=get_db_headers(),
            json={
                'user_id': user_id,
                'access_type': 'download',
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
                'success': True
            }
        )
        
        # Return file
        response = HttpResponse(decrypted_data, content_type=file_metadata['mime_type'])
        response['Content-Disposition'] = f'attachment; filename="{file_metadata["filename"]}"'
        return response
        
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        
        # Log failed access
        requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/log_access/",
            headers=get_db_headers(),
            json={
                'user_id': user_id,
                'access_type': 'download',
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
                'success': False,
                'error_message': str(e)
            }
        )
        
        return Response({
            'success': False,
            'error': 'Download failed',
            'message': 'An error occurred while downloading the file'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_user_files(request):
    """List all files for the authenticated user"""
    # Verify JWT token
    payload, error = verify_jwt_token(request)
    if error:
        return Response({
            'success': False,
            'error': error,
            'message': 'Authentication failed'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    user_id = payload.get('user_id')
    
    try:
        # Get user files from database
        response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/files/user_files/",
            params={'user_id': user_id},
            headers=get_db_headers()
        )
        
        if response.status_code == 200:
            files = response.json()
            return Response({
                'success': True,
                'files': files,
                'count': len(files)
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to retrieve files',
                'message': 'Could not get file list'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        return Response({
            'success': False,
            'error': 'List failed',
            'message': 'An error occurred while listing files'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_user_file(request, file_id):
    """Delete a file (mark as deleted)"""
    # Verify JWT token
    payload, error = verify_jwt_token(request)
    if error:
        return Response({
            'success': False,
            'error': error,
            'message': 'Authentication failed'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    user_id = payload.get('user_id')
    
    try:
        # Get file metadata from database
        response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/",
            headers=get_db_headers()
        )
        
        if response.status_code != 200:
            return Response({
                'success': False,
                'error': 'File not found',
                'message': 'The requested file does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        file_metadata = response.json()
        
        # Check if user owns the file
        if str(file_metadata['user']) != str(user_id):
            return Response({
                'success': False,
                'error': 'Unauthorized',
                'message': 'You do not have permission to delete this file'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Mark file as deleted in database
        delete_response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/mark_deleted/",
            headers=get_db_headers(),
            json={
                'user_id': user_id,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT')
            }
        )
        
        if delete_response.status_code == 200:
            # Delete physical file
            try:
                storage_path = file_metadata['storage_path']
                # logger.info(f"Attempting to delete file at: {storage_path}")
                
                if delete_file(storage_path):
                    pass
                    # logger.info(f"Successfully deleted file: {storage_path}")
                else:
                    logger.warning(f"File not found at: {storage_path}")
            except Exception as e:
                logger.error(f"Failed to delete physical file at {file_metadata['storage_path']}: {str(e)}")
            
            return Response({
                'success': True,
                'message': 'File deleted successfully',
                'file_id': file_id
            })
        else:
            return Response({
                'success': False,
                'error': 'Deletion failed',
                'message': 'Failed to delete file'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Deletion failed',
            'message': 'An error occurred while deleting the file'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'healthy',
        'service': 'file-service',
        'timestamp': datetime.now().isoformat()
    })