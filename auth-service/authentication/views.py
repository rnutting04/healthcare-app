from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.http import Http404
from django_ratelimit.decorators import ratelimit
import logging

logger = logging.getLogger(__name__)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    RefreshTokenSerializer, ChangePasswordSerializer
)
from .utils import (
    generate_access_token, generate_refresh_token,
    verify_refresh_token, invalidate_refresh_token,
    invalidate_all_user_tokens
)
from .permissions import IsOwnerOrAdmin
from .services import DatabaseService

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])  # Disable authentication for register endpoint
@ratelimit(key='ip', rate='5/m', method='POST')
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        # User is now a dictionary from database service
        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token(user)
        
        # Get the role name from the user's role_detail or role_name
        role_name = 'patient'  # default
        if 'role_detail' in user and user['role_detail']:
            role_name = user['role_detail'].get('name', 'patient').lower()
        elif 'role_name' in user:
            role_name = user['role_name'].lower()
        elif 'role' in serializer.validated_data:
            # Get role from serializer validated data
            role_name = serializer.validated_data['role'].lower()
        else:
            # Fallback: get from initial data
            role_name = serializer.initial_data.get('role', 'PATIENT').lower()
        
        # If the user is a patient, create a patient profile
        if role_name == 'patient':
            try:
                from .services import DatabaseService
                # Create patient profile with minimal data
                patient_data = {
                    'user_id': user['id'],
                    'preferred_language_id': 'en',  # Default to English (using code as PK)
                    # These fields will be filled later by the user
                    'date_of_birth': '1900-01-01',  # Placeholder
                    'gender': 'OTHER',  # Placeholder
                    'phone_number': '',
                    'address': '',
                    'emergency_contact_name': '',
                    'emergency_contact_phone': ''
                }
                DatabaseService.create_patient_profile(patient_data)
                logger.info(f"Created patient profile for user {user['id']}")
            except Exception as e:
                logger.error(f"Failed to create patient profile: {e}")
                # Don't fail the registration if patient profile creation fails
        
        response = Response({
            'user': UserSerializer(user).data,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'redirect_url': f'/{role_name}/dashboard'
        }, status=status.HTTP_201_CREATED)
        
        # Set secure cookies for session management
        from django.conf import settings
        
        response.set_cookie(
            'access_token',
            access_token,
            max_age=settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds(),
            httponly=True,
            samesite='Lax',
            secure=settings.SECURE_SSL_REDIRECT  # True in production
        )
        
        response.set_cookie(
            'refresh_token',
            refresh_token,
            max_age=settings.JWT_REFRESH_TOKEN_LIFETIME.total_seconds(),
            httponly=True,
            samesite='Lax',
            secure=settings.SECURE_SSL_REDIRECT  # True in production
        )
        
        return response
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])  # Disable authentication for login endpoint
@ratelimit(key='ip', rate='5/m', method='POST')
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        # Update last login via database service
        DatabaseService.update_user(user['id'], {'last_login': timezone.now().isoformat()})
        
        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token(user)
        
        # Check if there's a 'next' parameter in the request
        next_url = request.data.get('next', '')
        if next_url and next_url.startswith('/'):  # Ensure it's a relative URL for security
            redirect_url = next_url
        else:
            # Default redirect based on role
            redirect_url = f'/{user["role"]["name"].lower()}/dashboard'
        
        response = Response({
            'user': UserSerializer(user).data,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'redirect_url': redirect_url
        }, status=status.HTTP_200_OK)
        
        # Set secure cookies for session management
        # In production, these should have secure=True and samesite='Strict'
        from django.conf import settings
        
        response.set_cookie(
            'access_token',
            access_token,
            max_age=settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds(),
            httponly=True,
            samesite='Lax',
            secure=settings.SECURE_SSL_REDIRECT  # True in production
        )
        
        response.set_cookie(
            'refresh_token',
            refresh_token,
            max_age=settings.JWT_REFRESH_TOKEN_LIFETIME.total_seconds(),
            httponly=True,
            samesite='Lax',
            secure=settings.SECURE_SSL_REDIRECT  # True in production
        )
        
        return response
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def refresh_token(request):
    serializer = RefreshTokenSerializer(data=request.data)
    if serializer.is_valid():
        token = serializer.validated_data['refresh_token']
        refresh_token_obj = verify_refresh_token(token)
        
        if not refresh_token_obj:
            return Response({
                'error': 'Invalid or expired refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get user from database service
        user = DatabaseService.get_user_by_id(refresh_token_obj['user_id'])
        if not user:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        access_token = generate_access_token(user)
        
        return Response({
            'access_token': access_token
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    refresh_token = request.data.get('refresh_token')
    if refresh_token:
        invalidate_refresh_token(refresh_token)
    
    response = Response({
        'message': 'Successfully logged out'
    }, status=status.HTTP_200_OK)
    
    # Clear cookies
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    
    return response

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_all(request):
    invalidate_all_user_tokens(request.user)
    
    return Response({
        'message': 'Successfully logged out from all devices'
    }, status=status.HTTP_200_OK)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Get user from database service using ID from JWT
        user_id = getattr(self.request, 'user_id', None)
        if user_id:
            user = DatabaseService.get_user_by_id(user_id)
            return user
        return None

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_object(self):
        user_id = self.kwargs.get('pk')
        user = DatabaseService.get_user_by_id(user_id)
        if not user:
            raise Http404("User not found")
        return user

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        # Get user from database service
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response({
                'error': 'User not authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        user = DatabaseService.get_user_by_id(user_id)
        if not user:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        old_password = serializer.validated_data['old_password']
        
        # Check old password
        from django.contrib.auth.hashers import check_password
        if not check_password(old_password, user.get('password', '')):
            return Response({
                'error': 'Invalid old password'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update password via database service
        from django.contrib.auth.hashers import make_password
        new_password_hash = make_password(serializer.validated_data['new_password'])
        DatabaseService.update_user(user_id, {'password': new_password_hash})
        
        # Invalidate all tokens after password change
        invalidate_all_user_tokens({'id': user_id})
        
        return Response({
            'message': 'Password successfully changed. Please login again.'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def verify_token(request):
    # Get user from database service
    user_id = getattr(request, 'user_id', None)
    if not user_id:
        return Response({
            'valid': False,
            'error': 'User not authenticated'
        }, status=status.HTTP_401_UNAUTHORIZED)
        
    user = DatabaseService.get_user_by_id(user_id)
    if not user:
        return Response({
            'valid': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
        
    return Response({
        'valid': True,
        'user': UserSerializer(user).data
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def refresh_if_active(request):
    """
    Refresh token if user has been active.
    This endpoint checks the current token's age and only issues a new token
    if the token is at least 50% through its lifetime (7.5 minutes old).
    This prevents constant token regeneration while ensuring active users stay logged in.
    """
    from django.conf import settings
    import jwt
    
    # Get token from cookies or header
    access_token = request.COOKIES.get('access_token')
    if not access_token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
    
    if not access_token:
        return Response({'error': 'No token provided'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        # Decode the current token
        payload = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        # Check token age
        iat = payload.get('iat', 0)
        current_time = timezone.now().timestamp()
        token_age = current_time - iat
        token_lifetime = settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds()
        
        # Only refresh if token is at least 50% through its lifetime
        if token_age < (token_lifetime * 0.5):
            return Response({
                'message': 'Token is still fresh',
                'refreshed': False
            }, status=status.HTTP_200_OK)
        
        # Get user and generate new token
        user = User.objects.get(id=payload['user_id'])
        new_access_token = generate_access_token(user)
        
        response = Response({
            'access_token': new_access_token,
            'refreshed': True,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
        
        # Set the new token in cookies
        response.set_cookie(
            'access_token',
            new_access_token,
            max_age=settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds(),
            httponly=True,
            samesite='Lax',
            secure=settings.SECURE_SSL_REDIRECT
        )
        
        return response
        
    except jwt.ExpiredSignatureError:
        # Token has expired, user needs to login again
        return Response({'error': 'Token has expired'}, status=status.HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError:
        return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)