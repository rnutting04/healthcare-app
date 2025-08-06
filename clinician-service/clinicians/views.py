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
    TokenSerializer, RefreshTokenSerializer, ClinicianDashboardSerializer
)
import logging

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