from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
import jwt
from .models import User


class ServiceAuthentication(BaseAuthentication):
    """
    Custom authentication for internal service-to-service communication.
    This ensures only authenticated services can access the database API.
    """
    
    def authenticate(self, request):
        # Check for service token in headers
        service_token = request.META.get('HTTP_X_SERVICE_TOKEN')
        
        # For development/testing, also check for JWT token from auth service
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if service_token:
            # Validate service token
            expected_token = getattr(settings, 'SERVICE_TOKEN', None)
            if not expected_token:
                raise AuthenticationFailed('Service token not configured')
            
            if service_token != expected_token:
                raise AuthenticationFailed('Invalid service token')
            
            # Return None for user as this is service authentication
            return (None, 'service')
        
        elif auth_header:
            # Handle JWT token from auth service
            try:
                token = auth_header.split(' ')[1]
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=['HS256']
                )
                
                # Get user from payload
                user = User.objects.get(id=payload['user_id'])
                return (user, 'jwt')
                
            except jwt.ExpiredSignatureError:
                raise AuthenticationFailed('Token has expired')
            except jwt.InvalidTokenError:
                raise AuthenticationFailed('Invalid token')
            except User.DoesNotExist:
                raise AuthenticationFailed('User not found')
            except Exception:
                raise AuthenticationFailed('Authentication failed')
        
        return None


from rest_framework.permissions import BasePermission


class IsAuthenticatedOrService(BasePermission):
    """
    Permission class that allows access to authenticated users or internal services
    """
    def has_permission(self, request, view):
        # Allow if it's a service token
        if hasattr(request, 'auth') and request.auth == 'service':
            return True
        
        # Allow if user is authenticated
        if request.user and request.user.is_authenticated:
            return True
            
        return False