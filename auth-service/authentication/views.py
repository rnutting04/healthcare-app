from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from .models import User
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

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])  # Disable authentication for register endpoint
@ratelimit(key='ip', rate='5/m', method='POST')
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token(user)
        
        response = Response({
            'user': UserSerializer(user).data,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'redirect_url': f'/{user.role.name.lower()}/dashboard'
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
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token(user)
        
        response = Response({
            'user': UserSerializer(user).data,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'redirect_url': f'/{user.role.name.lower()}/dashboard'
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
        
        user = refresh_token_obj.user
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
        return self.request.user

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        old_password = serializer.validated_data['old_password']
        
        if not user.check_password(old_password):
            return Response({
                'error': 'Invalid old password'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Invalidate all tokens after password change
        invalidate_all_user_tokens(user)
        
        return Response({
            'message': 'Password successfully changed. Please login again.'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def verify_token(request):
    return Response({
        'valid': True,
        'user': UserSerializer(request.user).data
    }, status=status.HTTP_200_OK)