import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from .services import DatabaseService
import logging

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """Middleware to authenticate users based on JWT tokens in cookies."""
    
    def process_request(self, request):
        # Skip authentication for API endpoints (they use DRF authentication)
        if request.path.startswith('/api/'):
            return
        
        # Get token from cookies
        access_token = request.COOKIES.get('access_token')
        
        if not access_token:
            request.user = AnonymousUser()
            return
        
        try:
            # Decode the JWT token
            payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Get user from the payload
            user_id = payload.get('user_id')
            if user_id:
                try:
                    # Get user from database service
                    user_data = DatabaseService.get_user_by_id(user_id)
                    if user_data:
                        # Create a simple user object with required attributes
                        class SimpleUser:
                            def __init__(self, data):
                                self.id = data.get('id')
                                self.email = data.get('email')
                                self.first_name = data.get('first_name')
                                self.last_name = data.get('last_name')
                                self.is_active = data.get('is_active', True)
                                self.is_authenticated = True
                                self.is_anonymous = False
                                self.role_name = payload.get('role', 'PATIENT')
                                self.role = type('obj', (object,), {
                                    'name': self.role_name,
                                    'id': data.get('role', {}).get('id') if isinstance(data.get('role'), dict) else data.get('role_id')
                                })()
                            
                            def __str__(self):
                                return self.email
                        
                        request.user = SimpleUser(user_data)
                        request.user_id = user_id  # Store user_id separately for views
                    else:
                        request.user = AnonymousUser()
                except Exception as e:
                    logger.error(f"Failed to get user from database service: {e}")
                    request.user = AnonymousUser()
            else:
                request.user = AnonymousUser()
                
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            # logger.debug(f"JWT validation failed: {e}")
            request.user = AnonymousUser()