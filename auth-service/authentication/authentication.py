import jwt
from django.conf import settings
from django.utils import timezone
from rest_framework import authentication, exceptions
from .services import DatabaseService
import logging

logger = logging.getLogger(__name__)


class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header:
            return None
        
        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                raise exceptions.AuthenticationFailed('Invalid authentication header format.')
        except ValueError:
            raise exceptions.AuthenticationFailed('Invalid authentication header format.')
        
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Access token has expired.')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid access token.')
        
        try:
            user_id = payload.get('user_id')
            user_data = DatabaseService.get_user_by_id(user_id)
            
            if not user_data:
                raise exceptions.AuthenticationFailed('User not found.')
            
            if not user_data.get('is_active', False):
                raise exceptions.AuthenticationFailed('User account is disabled.')
            
            # Create a simple user object that DRF can work with
            class AuthenticatedUser:
                def __init__(self, data):
                    self.id = data.get('id')
                    self.pk = self.id  # DRF often uses pk
                    self.email = data.get('email')
                    self.first_name = data.get('first_name')
                    self.last_name = data.get('last_name')
                    self.is_active = data.get('is_active', True)
                    self.is_authenticated = True
                    self.is_anonymous = False
                    self._data = data  # Store original data
                    
                    # Handle role
                    if isinstance(data.get('role'), dict):
                        self.role = type('obj', (object,), {
                            'id': data['role']['id'],
                            'name': data['role']['name'],
                            'display_name': data['role'].get('display_name', ''),
                        })()
                    else:
                        # Fallback if role is just an ID
                        self.role = type('obj', (object,), {
                            'id': data.get('role_id'),
                            'name': payload.get('role', 'PATIENT'),
                        })()
                
                def __str__(self):
                    return self.email
                
                def to_dict(self):
                    """Convert back to dictionary for serialization"""
                    return self._data
            
            user = AuthenticatedUser(user_data)
            
            # Store user_id in request for easy access
            request.user_id = user_id
            
            return (user, token)
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise exceptions.AuthenticationFailed('Authentication failed.')