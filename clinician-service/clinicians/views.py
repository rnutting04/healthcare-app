from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict
import jwt
import uuid
from .services import DatabaseService
from django.conf import settings
from .serializers import (
    ClinicianRegistrationSerializer, ClinicianLoginSerializer,
    ClinicianSerializer, ClinicianProfileUpdateSerializer,
    TokenSerializer, RefreshTokenSerializer, ClinicianDashboardSerializer,
    PatientListSerializer
)
import logging
import requests
from django.http import HttpResponse, JsonResponse
import redis
import json

logger = logging.getLogger(__name__)


class ClinicianAuthViewSet(viewsets.ViewSet):
    """ViewSet for clinician authentication"""
    
    @action(detail=False, methods=['post'])
    def signup(self, request):
        """Register a new clinician"""
        print(f"Signup request data: {request.data}")
        serializer = ClinicianRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        print(f"Validated data: {validated_data}")
        
        try:
            # Check if user already exists
            existing_user = DatabaseService.get_user_by_email(validated_data['email'])
            if existing_user:
                return Response(
                    {'error': 'User with this email already exists'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create user with CLINICIAN role
            user_data = {
                'email': validated_data['email'],
                'password': validated_data['password'],
                'first_name': validated_data['first_name'],
                'last_name': validated_data['last_name'],
                'role': 'CLINICIAN'
            }
            
            user = DatabaseService.create_user(user_data)
            logger.info(f"Created user: {user}")
            
            # Create clinician profile
            clinician_data = {
                'user_id': user['id'],
                'specialization_id': validated_data['specialization_id'],
                'phone_number': validated_data['phone_number']
            }
            logger.info(f"Creating clinician with data: {clinician_data}")
            
            clinician = DatabaseService.create_clinician(clinician_data)
            logger.info(f"Created clinician: {clinician}")
            
            # Log event
            DatabaseService.log_event('clinician_registered', 'clinician-service', {
                'user_id': user['id'],
                'clinician_id': clinician['id']
            })
            
            # Generate tokens
            tokens = self._generate_tokens(user)
            
            return Response({
                'user': user,
                'clinician': clinician,
                'tokens': tokens
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Signup failed: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """Login a clinician"""
        serializer = ClinicianLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        try:
            # Authenticate user
            user = DatabaseService.authenticate_user(
                validated_data['email'],
                validated_data['password']
            )
            
            if not user:
                return Response(
                    {'error': 'Invalid credentials'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user is a clinician
            if user.get('role_name') != 'CLINICIAN':
                return Response(
                    {'error': 'Access denied. Clinicians only.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(user['id'])
            
            # Log event
            DatabaseService.log_event('clinician_login', 'clinician-service', {
                'user_id': user['id']
            })
            
            # Generate tokens
            tokens = self._generate_tokens(user)
            
            return Response({
                'user': user,
                'clinician': clinician,
                'tokens': tokens
            })
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Logout a clinician"""
        # Get refresh token from request
        refresh_token = request.data.get('refresh')
        
        if refresh_token:
            # Invalidate the refresh token
            DatabaseService.invalidate_refresh_token(refresh_token)
        
        # Log event
        if hasattr(request, 'user_id'):
            DatabaseService.log_event('clinician_logout', 'clinician-service', {
                'user_id': request.user_id
            })
        
        return Response({'message': 'Successfully logged out'})
    
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """Refresh access token"""
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        refresh_token = serializer.validated_data['refresh']
        
        try:
            # Verify refresh token
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Check if token exists in database
            token_record = DatabaseService.get_refresh_token(refresh_token)
            if not token_record or not token_record.get('is_active'):
                return Response(
                    {'error': 'Invalid refresh token'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get user
            user = DatabaseService.get_user(payload['user_id'])
            if not user:
                return Response(
                    {'error': 'User not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Generate new access token
            access_token = self._generate_access_token(user)
            
            return Response({
                'access': access_token
            })
            
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Refresh token expired'}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def refresh_if_active(self, request):
        """Refresh access token if user is active (for automatic refresh)"""
        # Check if user has valid session
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return Response({'active': False}, status=status.HTTP_200_OK)
        
        access_token = auth_header.split(' ')[1]
        
        try:
            # Try to decode the current access token
            payload = jwt.decode(
                access_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False}  # Don't verify expiration yet
            )
            
            # Check if token is expired or about to expire (within 5 minutes)
            exp_timestamp = payload.get('exp', 0)
            current_timestamp = timezone.now().timestamp()
            time_until_expiry = exp_timestamp - current_timestamp
            
            if time_until_expiry > 300:  # More than 5 minutes until expiry
                return Response({
                    'active': True,
                    'needs_refresh': False
                }, status=status.HTTP_200_OK)
            
            # Token is expired or about to expire, check for refresh token
            refresh_token = request.COOKIES.get('refresh_token')
            if not refresh_token:
                return Response({'active': False}, status=status.HTTP_200_OK)
            
            # Try to refresh the token
            try:
                # Verify refresh token
                refresh_payload = jwt.decode(
                    refresh_token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM]
                )
                
                # Check if refresh token exists in database
                token_record = DatabaseService.get_refresh_token(refresh_token)
                if not token_record or not token_record.get('is_active'):
                    return Response({'active': False}, status=status.HTTP_200_OK)
                
                # Get user
                user = DatabaseService.get_user(refresh_payload['user_id'])
                if not user:
                    return Response({'active': False}, status=status.HTTP_200_OK)
                
                # Generate new access token
                new_access_token = self._generate_access_token(user)
                
                return Response({
                    'active': True,
                    'needs_refresh': True,
                    'access': new_access_token
                }, status=status.HTTP_200_OK)
                
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                return Response({'active': False}, status=status.HTTP_200_OK)
                
        except (jwt.InvalidTokenError, KeyError):
            return Response({'active': False}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Refresh if active check failed: {e}")
            return Response({'active': False}, status=status.HTTP_200_OK)
    
    def _generate_tokens(self, user: Dict) -> Dict[str, str]:
        """Generate access and refresh tokens"""
        access_token = self._generate_access_token(user)
        refresh_token = self._generate_refresh_token(user)
        
        # Store refresh token in database
        expires_at = timezone.now() + timedelta(minutes=settings.JWT_REFRESH_TOKEN_LIFETIME)
        DatabaseService.create_refresh_token(
            user_id=user['id'],
            token=refresh_token,
            expires_at=expires_at.isoformat()
        )
        
        return {
            'access': access_token,
            'refresh': refresh_token
        }
    
    def _generate_access_token(self, user: Dict) -> str:
        """Generate access token"""
        payload = {
            'user_id': user['id'],
            'email': user['email'],
            'role': user.get('role_name', 'CLINICIAN'),
            'exp': timezone.now() + timedelta(minutes=15),
            'iat': timezone.now(),
            'jti': str(uuid.uuid4())
        }
        
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
    
    def _generate_refresh_token(self, user: Dict) -> str:
        """Generate refresh token"""
        payload = {
            'user_id': user['id'],
            'token_type': 'refresh',
            'exp': timezone.now() + timedelta(days=1),
            'iat': timezone.now(),
            'jti': str(uuid.uuid4())
        }
        
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )


class ClinicianProfileView(APIView):
    """View for clinician profile management"""
    
    def get(self, request):
        """Get current clinician's profile"""
        try:
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            if not clinician:
                return Response(
                    {'error': 'Clinician profile not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Add user data
            user = DatabaseService.get_user(request.user_id)
            if user:
                clinician['user'] = user
            
            serializer = ClinicianSerializer(clinician)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        """Update clinician profile"""
        serializer = ClinicianProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get current clinician
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            if not clinician:
                return Response(
                    {'error': 'Clinician profile not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Update user data if provided
            user_updates = {}
            if 'first_name' in serializer.validated_data:
                user_updates['first_name'] = serializer.validated_data.pop('first_name')
            if 'last_name' in serializer.validated_data:
                user_updates['last_name'] = serializer.validated_data.pop('last_name')
            
            if user_updates:
                # Update user via database service
                # Note: This would require a new endpoint in database service
                pass
            
            # Update clinician profile
            updated_clinician = DatabaseService.update_clinician(
                clinician['id'], 
                serializer.validated_data
            )
            
            # Log event
            DatabaseService.log_event('clinician_profile_updated', 'clinician-service', {
                'user_id': request.user_id,
                'clinician_id': clinician['id']
            })
            
            # Add user data
            user = DatabaseService.get_user(request.user_id)
            if user:
                updated_clinician['user'] = user
            
            return Response(ClinicianSerializer(updated_clinician).data)
            
        except Exception as e:
            logger.error(f"Failed to update profile: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ClinicianDashboardView(APIView):
    """View for clinician dashboard data"""
    
    def get(self, request):
        """Get clinician dashboard data"""
        try:
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            
            # Prepare dashboard data (stub implementation)
            dashboard_data = {
                'user_id': request.user_id,
                'first_name': request.user_data.get('first_name', 'Clinician'),
                'last_name': request.user_data.get('last_name', ''),
                'email': request.user_data.get('email', ''),
                'clinician_profile': clinician,
                
                # Stub statistics
                'total_patients': 0,
                'today_appointments': 0,
                'pending_appointments': 0,
                
                # Empty lists for now
                'upcoming_appointments': [],
                'recent_patients': []
            }
            
            if clinician:
                # In a real implementation, these would fetch actual data
                # For now, just return stub data
                pass
            
            serializer = ClinicianDashboardSerializer(dashboard_data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return Response(
                {'error': 'Failed to load dashboard'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClinicianPatientsView(APIView):
    """View for retrieving patients assigned to the logged-in clinician"""
    
    def get(self, request):
        """Get all patients assigned to the current clinician"""
        try:
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            if not clinician:
                return Response(
                    {'error': 'Clinician profile not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get patients assigned to this clinician
            patients = DatabaseService.get_clinician_patients(clinician['id'])
            
            # Log event
            DatabaseService.log_event('clinician_viewed_patients', 'clinician-service', {
                'user_id': request.user_id,
                'clinician_id': clinician['id'],
                'patient_count': len(patients)
            })
            
            serializer = PatientListSerializer(patients, many=True)
            return Response({
                'count': len(patients),
                'results': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Failed to get patient list: {e}")
            return Response(
                {'error': 'Failed to retrieve patient list'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PatientDetailView(APIView):
    """View for retrieving and managing a specific patient's details"""
    
    def get(self, request, patient_id):
        """Get patient details - only accessible by assigned clinician"""
        try:
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            if not clinician:
                return Response(
                    {'error': 'Clinician profile not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get patient details
            patient = DatabaseService.get_patient(patient_id)
            if not patient:
                return Response(
                    {'error': 'Patient not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if this clinician is assigned to the patient
            assignment = patient.get('assignment')
            if not assignment or assignment.get('assigned_clinician') != clinician['id']:
                logger.warning(f"Clinician {clinician['id']} attempted to access unassigned patient {patient_id}")
                return Response(
                    {'error': 'Access denied. You are not assigned to this patient.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get user data for the patient
            if patient.get('user_id'):
                user = DatabaseService.get_user(patient['user_id'])
                if user:
                    patient['user'] = user
            
            # Log access
            DatabaseService.log_event('clinician_viewed_patient_detail', 'clinician-service', {
                'user_id': request.user_id,
                'clinician_id': clinician['id'],
                'patient_id': patient_id
            })
            
            # Prepare response with stub data
            response_data = {
                'patient': patient,
                'medical_records': [],  # Stub
                'prescriptions': [],    # Stub
                'appointments': [],     # Stub
                'recent_activity': []   # Stub
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Failed to get patient details: {e}")
            return Response(
                {'error': 'Failed to retrieve patient details'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PatientDashboardView(APIView):
    """Template view for patient dashboard - only accessible by assigned clinician"""
    
    def get(self, request, patient_id):
        """Render patient dashboard template"""
        try:
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            if not clinician:
                return Response(
                    {'error': 'Clinician profile not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if clinician is assigned to this patient
            assignment = DatabaseService.get_patient_assignment(patient_id, clinician['id'])
            if not assignment:
                return Response(
                    {'error': 'You are not authorized to view this patient'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get patient details
            patient = DatabaseService.get_patient(patient_id)
            if not patient:
                return Response(
                    {'error': 'Patient not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get user info
            if patient.get('user_id'):
                user = DatabaseService.get_user(patient['user_id'])
                if user:
                    patient['user'] = user
            
            # Log access
            DatabaseService.log_event('clinician_accessed_patient_dashboard', 'clinician-service', {
                'user_id': request.user_id,
                'clinician_id': clinician['id'],
                'patient_id': patient_id
            })
            
            # Get user info for template
            user = DatabaseService.get_user(request.user_id)
            
            # Debug logging
            logger.info(f"Patient data: {patient}")
            logger.info(f"Patient fields: date_of_birth={patient.get('date_of_birth')}, gender={patient.get('gender')}, phone={patient.get('phone_number')}")
            if patient.get('user'):
                logger.info(f"Patient user data: {patient['user']}")
            
            # Print all keys in patient dict
            logger.info(f"Patient keys: {list(patient.keys()) if isinstance(patient, dict) else 'Not a dict'}")
            
            # Prepare context for template
            context = {
                'user': user,
                'clinician': clinician,
                'patient': patient,
                'medical_records': [],  # Stub - will be implemented later
                'prescriptions': [],    # Stub - will be implemented later
                'appointments': [],     # Stub - will be implemented later
                'recent_activity': []   # Stub - will be implemented later
            }
            
            logger.info(f"Context patient data being sent to template: {context['patient']}")
            
            from django.shortcuts import render
            from django.http import HttpResponse
            
            # For debugging, also return raw data
            if request.GET.get('debug') == '1':
                import json
                return HttpResponse(json.dumps(context, indent=2, default=str), content_type='application/json')
            
            return render(request, 'patient_dashboard.html', context)
            
        except Exception as e:
            logger.error(f"Failed to load patient dashboard: {e}")
            return Response(
                {'error': 'Failed to load patient dashboard'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MedicalRecordDownloadView(APIView):
    """View for downloading medical records"""
    
    def get(self, request, file_id):
        """Download a medical record file"""
        try:
            # Forward the request to file-service's medical record download endpoint
            headers = {'Authorization': request.META.get('HTTP_AUTHORIZATION', '')}
            
            response = requests.get(
                f"{settings.FILE_SERVICE_URL}/api/files/medical-records/{file_id}/download",
                headers=headers,
                stream=True
            )
            
            if response.status_code == 200:
                # Create Django response with file content
                django_response = HttpResponse(
                    response.content,
                    content_type=response.headers.get('Content-Type', 'application/octet-stream')
                )
                
                # Copy content-disposition header
                if 'Content-Disposition' in response.headers:
                    django_response['Content-Disposition'] = response.headers['Content-Disposition']
                
                return django_response
            else:
                # Try to get error details from response
                try:
                    error_data = response.json()
                    return Response(error_data, status=response.status_code)
                except:
                    return Response(
                        {'error': 'Failed to download file'},
                        status=response.status_code
                    )
                
        except Exception as e:
            logger.error(f"Failed to download medical record: {e}")
            return Response(
                {'error': 'Failed to download medical record'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MedicalRecordDeleteView(APIView):
    """View for deleting medical records"""
    
    def delete(self, request, file_id):
        """Delete a medical record - delegates to file-service for complete cleanup"""
        try:
            # Forward the delete request to file-service which handles all cleanup
            headers = {'Authorization': request.META.get('HTTP_AUTHORIZATION', '')}
            
            response = requests.delete(
                f"{settings.FILE_SERVICE_URL}/api/files/medical-records/{file_id}/delete",
                headers=headers
            )
            
            if response.status_code == 200:
                return Response(
                    response.json(),
                    status=status.HTTP_200_OK
                )
            else:
                # Pass through the error response from file-service
                try:
                    error_data = response.json()
                    return Response(error_data, status=response.status_code)
                except:
                    return Response(
                        {'error': 'Failed to delete medical record'},
                        status=response.status_code
                    )
                
        except Exception as e:
            logger.error(f"Failed to delete medical record: {e}")
            return Response(
                {'error': 'Failed to delete medical record'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MedicalRecordViewView(APIView):
    """View for viewing medical records inline using temporary files"""
    
    def post(self, request, file_id):
        """Create a temporary copy of the medical record for viewing"""
        try:
            # Get JWT token from cookie or header (NOT from URL)
            token = request.COOKIES.get('access_token')
            if not token:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
            
            if not token:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Download the file from file-service
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{settings.FILE_SERVICE_URL}/api/files/medical-records/{file_id}/download?view=true",
                headers=headers,
                stream=True
            )
            
            if response.status_code == 200:
                # Create temporary directory if it doesn't exist
                import os
                import tempfile
                
                temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_medical_records')
                os.makedirs(temp_dir, exist_ok=True)
                
                # Generate unique filename
                temp_filename = f"{uuid.uuid4()}.pdf"
                temp_path = os.path.join(temp_dir, temp_filename)
                
                # Save decrypted content to temporary file
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Store temp file info in Redis for cleanup
                r = redis.from_url(settings.REDIS_URL, decode_responses=True)
                user_id = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
                redis_key = f"temp_files:user:{user_id}:{temp_filename}"
                temp_file_data = {
                    'path': temp_path,
                    'created_at': str(datetime.now()),
                    'file_id': file_id,
                    'user_id': user_id
                }
                # Set with 1 hour expiry
                r.setex(redis_key, 3600, json.dumps(temp_file_data))
                
                # Clean up old temporary files
                self._cleanup_old_temp_files(user_id)
                
                # Return URL to access the temporary file
                temp_url = f"/media/temp_medical_records/{temp_filename}"
                
                return Response({
                    'success': True,
                    'temp_url': temp_url,
                    'temp_id': temp_filename
                })
            else:
                return Response(
                    {'error': 'Failed to retrieve file'},
                    status=response.status_code
                )
                
        except Exception as e:
            logger.error(f"Failed to create temporary medical record: {e}")
            return Response(
                {'error': 'Failed to create temporary file'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _cleanup_old_temp_files(self, user_id):
        """Clean up temporary files older than 1 hour"""
        try:
            import os
            from datetime import datetime, timedelta
            
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            pattern = f"temp_files:user:{user_id}:*"
            
            for key in r.scan_iter(match=pattern):
                try:
                    file_data = json.loads(r.get(key))
                    created_at = datetime.fromisoformat(file_data['created_at'])
                    
                    if datetime.now() - created_at > timedelta(hours=1):
                        # Delete old file
                        if os.path.exists(file_data['path']):
                            os.remove(file_data['path'])
                            logger.info(f"Cleaned up old temporary file: {file_data['path']}")
                        r.delete(key)
                except Exception as e:
                    logger.error(f"Error processing temp file {key}: {e}")
                
        except Exception as e:
            logger.error(f"Error cleaning up old temp files: {e}")


class TempFileCleanupView(APIView):
    """View for cleaning up temporary medical record files"""
    
    def post(self, request):
        """Clean up temporary file when modal is closed"""
        try:
            import os
            
            # Get temp_id from request
            temp_id = request.data.get('temp_id')
            if not temp_id:
                return Response(
                    {'error': 'No temporary file ID provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get JWT token to identify user
            token = request.COOKIES.get('access_token')
            if not token:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
            
            if not token:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get user ID from token
            user_id = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
            
            # Get temp file info from Redis
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_key = f"temp_files:user:{user_id}:{temp_id}"
            
            temp_data = r.get(redis_key)
            if temp_data:
                temp_info = json.loads(temp_data)
                temp_path = temp_info['path']
                
                # Delete the temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.info(f"Deleted temporary file: {temp_path}")
                
                # Remove from Redis
                r.delete(redis_key)
                
                return Response({
                    'success': True,
                    'message': 'Temporary file deleted'
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Temporary file not found'
                })
                
        except Exception as e:
            logger.error(f"Failed to delete temporary file: {e}")
            return Response(
                {'error': 'Failed to delete temporary file'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )