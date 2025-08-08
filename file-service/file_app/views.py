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


@api_view(['POST'])
@csrf_exempt
def upload_medical_record(request):
    """
    Upload a medical record with hybrid encryption.
    File is encrypted with a unique key, then that key is encrypted for each authorized user.
    """
    # Verify JWT token
    payload, error = verify_jwt_token(request)
    if error:
        return Response({
            'success': False,
            'error': error,
            'message': 'Authentication failed'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    clinician_user_id = payload.get('user_id')
    
    # Get required parameters
    patient_id = request.POST.get('patient_id')
    medical_record_type_id = request.POST.get('medical_record_type_id')
    
    if not patient_id or not medical_record_type_id:
        return Response({
            'success': False,
            'error': 'Missing parameters',
            'message': 'patient_id and medical_record_type_id are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
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
        # Verify clinician is assigned to patient
        verify_response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/patient-assignments/check_assignment/",
            params={'patient_id': patient_id, 'clinician_user_id': clinician_user_id},
            headers=get_db_headers()
        )
        
        if verify_response.status_code != 200 or not verify_response.json().get('is_assigned'):
            return Response({
                'success': False,
                'error': 'Unauthorized',
                'message': 'You are not authorized to upload records for this patient'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate unique encryption key for this medical record
        from cryptography.fernet import Fernet
        record_encryption_key = Fernet.generate_key()
        
        # Encrypt the file with the record key
        uploaded_file.seek(0)
        encrypted_data = encrypt_file(uploaded_file, record_encryption_key)
        
        # Calculate file hash
        uploaded_file.seek(0)
        file_hash = calculate_file_hash(uploaded_file)
        
        # Generate storage path
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(uploaded_file.name)[1]
        storage_filename = f"{file_id}{file_extension}"
        # Store in medical_records directory under patient ID
        storage_path = os.path.join(settings.FILE_STORAGE_PATH, 'medical_records', str(patient_id), storage_filename)
        
        # Save encrypted file
        save_encrypted_file(encrypted_data, storage_path)
        
        # Create file metadata
        metadata_response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/create_metadata/",
            headers=get_db_headers(),
            json={
                'user_id': clinician_user_id,  # File owner is the uploader
                'filename': uploaded_file.name,
                'file_hash': file_hash,
                'file_size': uploaded_file.size,
                'mime_type': uploaded_file.content_type or 'application/octet-stream',
                'storage_path': storage_path,
                'is_encrypted': True,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT')
            }
        )
        
        if metadata_response.status_code != 201:
            # Clean up file if metadata creation fails
            delete_file(storage_path)
            return Response({
                'success': False,
                'error': 'Metadata creation failed',
                'message': 'Failed to save file metadata'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        file_data = metadata_response.json()
        file_id = file_data['id']
        
        # Create medical record entry
        medical_record_response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/medical-records/",
            headers=get_db_headers(),
            json={
                'file': file_id,
                'patient': patient_id,
                'medical_record_type': medical_record_type_id,
                'uploaded_by': clinician_user_id,
                'record_encryption_key': record_encryption_key.decode()  # Store for emergency access
            }
        )
        
        if medical_record_response.status_code != 201:
            # Clean up on failure
            requests.delete(
                f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/",
                headers=get_db_headers()
            )
            delete_file(storage_path)
            return Response({
                'success': False,
                'error': 'Medical record creation failed',
                'message': 'Failed to create medical record entry'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get patient user ID
        patient_response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/patients/{patient_id}/",
            headers=get_db_headers()
        )
        patient_user_id = patient_response.json().get('user_id')
        
        # Create access entries for both patient and clinician
        medical_record_id = medical_record_response.json()['file']
        
        # Grant access to patient
        if patient_user_id:
            patient_key = get_user_encryption_key(patient_user_id)
            if patient_key:
                # Encrypt record key with patient's key
                patient_fernet = Fernet(patient_key.encode())
                encrypted_key_for_patient = patient_fernet.encrypt(record_encryption_key).decode()
                
                requests.post(
                    f"{settings.DATABASE_SERVICE_URL}/api/medical-record-access/",
                    headers=get_db_headers(),
                    json={
                        'medical_record': medical_record_id,
                        'user': patient_user_id,
                        'encrypted_access_key': encrypted_key_for_patient,
                        'granted_by': clinician_user_id
                    }
                )
        
        # Grant access to clinician
        clinician_key = get_user_encryption_key(clinician_user_id)
        if clinician_key:
            logger.info(f"Clinician key for user {clinician_user_id}: length={len(clinician_key)}")
            logger.info(f"Upload - User {clinician_user_id} key (first 20 chars): {clinician_key[:20]}")
            logger.info(f"Record encryption key: length={len(record_encryption_key)}")
            
            # Encrypt record key with clinician's key
            clinician_fernet = Fernet(clinician_key.encode())
            encrypted_key_for_clinician = clinician_fernet.encrypt(record_encryption_key).decode()
            
            logger.info(f"Encrypted key for clinician: length={len(encrypted_key_for_clinician)}")
            logger.info(f"First 50 chars of encrypted key: {encrypted_key_for_clinician[:50]}")
            
            # Test decryption immediately
            try:
                test_decrypt = clinician_fernet.decrypt(encrypted_key_for_clinician.encode())
                logger.info(f"Test decryption successful: {test_decrypt == record_encryption_key}")
            except Exception as e:
                logger.error(f"Test decryption failed: {e}")
            
            access_response = requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/medical-record-access/",
                headers=get_db_headers(),
                json={
                    'medical_record': medical_record_id,
                    'user': clinician_user_id,
                    'encrypted_access_key': encrypted_key_for_clinician,
                    'granted_by': clinician_user_id
                }
            )
            
            if access_response.status_code == 201:
                logger.info(f"Successfully created access for clinician {clinician_user_id}")
            else:
                logger.error(f"Failed to create access for clinician: {access_response.status_code}")
                logger.error(f"Response: {access_response.text}")
        
        # Log the upload
        requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/log_access/",
            headers=get_db_headers(),
            json={
                'user_id': clinician_user_id,
                'access_type': 'upload',
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
                'success': True
            }
        )
        
        return Response({
            'success': True,
            'message': 'Medical record uploaded successfully',
            'file_id': file_id,
            'medical_record_id': medical_record_id,
            'filename': uploaded_file.name,
            'uploaded_at': file_data['uploaded_at'],
            'size': uploaded_file.size,
            'mime_type': uploaded_file.content_type
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Medical record upload error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Upload failed',
            'message': 'An error occurred during medical record upload'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@csrf_exempt
def delete_medical_record(request, file_id):
    """
    Delete a medical record - handles all cleanup:
    1. Delete medical record access entries
    2. Delete medical record entry
    3. Log the deletion
    4. Mark file as deleted
    5. Delete physical file
    """
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
        # Get the medical record to verify it exists and check permissions
        medical_records_response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/medical-records/",
            params={'file': file_id},
            headers=get_db_headers()
        )
        
        if medical_records_response.status_code != 200:
            return Response({
                'success': False,
                'error': 'Medical record not found',
                'message': 'The requested medical record does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        medical_records_data = medical_records_response.json()
        
        # Handle paginated response
        if isinstance(medical_records_data, dict) and 'results' in medical_records_data:
            medical_records = medical_records_data['results']
        else:
            medical_records = medical_records_data
        
        if not medical_records:
            return Response({
                'success': False,
                'error': 'Medical record not found',
                'message': 'The requested medical record does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        medical_record = medical_records[0] if isinstance(medical_records, list) else medical_records
        
        # Verify the user uploaded this record (only uploader can delete)
        if medical_record.get('uploaded_by') != user_id:
            return Response({
                'success': False,
                'error': 'Unauthorized',
                'message': 'You can only delete medical records you uploaded'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Step 1: Delete all medical record access entries
        access_response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/medical-record-access/",
            params={'medical_record_id': file_id},
            headers=get_db_headers()
        )
        
        if access_response.status_code == 200:
            access_data = access_response.json()
            
            # Handle paginated response
            if isinstance(access_data, dict) and 'results' in access_data:
                access_list = access_data['results']
            else:
                access_list = access_data if isinstance(access_data, list) else []
            
            for access in access_list:
                requests.delete(
                    f"{settings.DATABASE_SERVICE_URL}/api/medical-record-access/{access['id']}/",
                    headers=get_db_headers()
                )
            
            logger.info(f"Deleted {len(access_list)} medical record access entries for file {file_id}")
        
        # Step 2: Delete the medical record entry
        medical_delete_response = requests.delete(
            f"{settings.DATABASE_SERVICE_URL}/api/medical-records/{file_id}/",
            headers=get_db_headers()
        )
        
        if medical_delete_response.status_code not in [200, 204]:
            logger.error(f"Failed to delete medical record entry: {medical_delete_response.status_code}")
        else:
            logger.info(f"Deleted medical record entry for file {file_id}")
        
        # Step 3: Log the deletion in file access log
        requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/log_access/",
            headers=get_db_headers(),
            json={
                'user_id': user_id,
                'access_type': 'delete_medical_record',
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
                'success': True
            }
        )
        
        # Step 4: Mark file as deleted in file_metadata
        mark_deleted_response = requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/mark_deleted/",
            headers=get_db_headers(),
            json={
                'user_id': user_id,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT')
            }
        )
        
        if mark_deleted_response.status_code == 200:
            # Step 5: Delete physical file
            try:
                # Get file metadata to find storage path
                file_response = requests.get(
                    f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/",
                    headers=get_db_headers()
                )
                
                if file_response.status_code == 200:
                    file_metadata = file_response.json()
                    storage_path = file_metadata.get('storage_path')
                    
                    if storage_path and delete_file(storage_path):
                        logger.info(f"Successfully deleted physical file: {storage_path}")
                    else:
                        logger.warning(f"Could not delete physical file: {storage_path}")
                
            except Exception as e:
                logger.error(f"Error deleting physical file: {str(e)}")
            
            return Response({
                'success': True,
                'message': 'Medical record and all associated data deleted successfully',
                'file_id': file_id
            })
        else:
            return Response({
                'success': False,
                'error': 'Deletion partially failed',
                'message': 'Some components could not be deleted'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Medical record deletion error: {str(e)}")
        
        # Log failed deletion attempt
        try:
            requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/log_access/",
                headers=get_db_headers(),
                json={
                    'user_id': user_id,
                    'access_type': 'delete_medical_record',
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT'),
                    'success': False,
                    'error_message': str(e)
                }
            )
        except:
            pass
        
        return Response({
            'success': False,
            'error': 'Deletion failed',
            'message': 'An error occurred while deleting the medical record'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def download_medical_record(request, file_id):
    """Download or view a medical record using hybrid encryption"""
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
        # Get medical record access
        access_response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/medical-record-access/",
            params={'user_id': user_id, 'medical_record_id': file_id},
            headers=get_db_headers()
        )
        
        if access_response.status_code != 200:
            logger.error(f"Access check failed: {access_response.status_code}")
            return Response({
                'success': False,
                'error': 'Access check failed',
                'message': 'Failed to verify access permissions'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        access_data = access_response.json()
        
        # Handle paginated response
        if isinstance(access_data, dict) and 'results' in access_data:
            access_list = access_data.get('results', [])
        else:
            access_list = access_data if isinstance(access_data, list) else []
        
        if not access_list:
            return Response({
                'success': False,
                'error': 'Unauthorized',
                'message': 'You do not have permission to access this medical record'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get the encrypted access key
        access_record = access_list[0]
        encrypted_access_key = access_record.get('encrypted_access_key')
        
        if not encrypted_access_key:
            logger.error(f"No encrypted access key found for user {user_id} and medical record {file_id}")
            return Response({
                'success': False,
                'error': 'Access key not found',
                'message': 'No access key found for this medical record'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get user's encryption key to decrypt the access key
        user_encryption_key = get_user_encryption_key(user_id)
        if not user_encryption_key:
            return Response({
                'success': False,
                'error': 'Encryption key error',
                'message': 'Failed to retrieve user encryption key'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.info(f"Retrieved user key for {user_id}: length={len(user_encryption_key)}")
        
        # Decrypt the medical record's encryption key
        from cryptography.fernet import Fernet
        try:
            # Compare keys during upload and download
            logger.info(f"Download - User {user_id} key (first 20 chars): {user_encryption_key[:20]}")
            logger.info(f"Download - Encrypted access key (first 50 chars): {encrypted_access_key[:50]}")
            
            # The user_encryption_key from database is already a string
            user_fernet = Fernet(user_encryption_key.encode())
            
            # The encrypted_access_key is already a string (base64 encoded), just encode to bytes
            record_encryption_key = user_fernet.decrypt(encrypted_access_key.encode())
            
            logger.info(f"Successfully decrypted access key for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to decrypt access key: {str(e)}")
            logger.error(f"Decryption error type: {type(e).__name__}")
            logger.error(f"User ID: {user_id}")
            logger.error(f"User encryption key length: {len(user_encryption_key) if user_encryption_key else 'None'}")
            logger.error(f"Encrypted access key length: {len(encrypted_access_key) if encrypted_access_key else 'None'}")
            return Response({
                'success': False,
                'error': 'Decryption failed',
                'message': 'Failed to decrypt medical record access key'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get file metadata
        file_response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/",
            headers=get_db_headers()
        )
        
        if file_response.status_code != 200:
            return Response({
                'success': False,
                'error': 'File not found',
                'message': 'The requested file does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        file_metadata = file_response.json()
        
        # Check if file is deleted
        if file_metadata.get('is_deleted'):
            return Response({
                'success': False,
                'error': 'File deleted',
                'message': 'This file has been deleted'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Read and decrypt file using the record's encryption key
        try:
            encrypted_data = read_encrypted_file(file_metadata['storage_path'])
            decrypted_data = decrypt_file(encrypted_data, record_encryption_key)
        except Exception as e:
            logger.error(f"Failed to read/decrypt file: {str(e)}")
            return Response({
                'success': False,
                'error': 'File read error',
                'message': 'Failed to read or decrypt the file'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Log access
        requests.post(
            f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/log_access/",
            headers=get_db_headers(),
            json={
                'user_id': user_id,
                'access_type': 'view_medical_record' if request.GET.get('view') == 'true' else 'download_medical_record',
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
                'success': True
            }
        )
        
        # Return file
        response = HttpResponse(decrypted_data, content_type=file_metadata['mime_type'])
        
        # Check if this is for viewing (inline) or downloading
        disposition = 'inline' if request.GET.get('view') == 'true' else 'attachment'
        response['Content-Disposition'] = f'{disposition}; filename="{file_metadata["filename"]}"'
        
        # For PDFs, ensure proper content type
        if file_metadata['filename'].lower().endswith('.pdf'):
            response['Content-Type'] = 'application/pdf'
        
        # Remove X-Frame-Options to allow iframe embedding
        if 'X-Frame-Options' in response:
            del response['X-Frame-Options']
        
        return response
        
    except Exception as e:
        logger.error(f"Medical record download error: {str(e)}")
        
        # Log failed access
        try:
            requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/files/{file_id}/log_access/",
                headers=get_db_headers(),
                json={
                    'user_id': user_id,
                    'access_type': 'download_medical_record',
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT'),
                    'success': False,
                    'error_message': str(e)
                }
            )
        except:
            pass
        
        return Response({
            'success': False,
            'error': 'Download failed',
            'message': 'An error occurred while downloading the medical record'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'healthy',
        'service': 'file-service',
        'timestamp': datetime.now().isoformat()
    })