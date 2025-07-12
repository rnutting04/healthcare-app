import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from authentication.models import User

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
                    user = User.objects.select_related('role').get(id=user_id)
                    # Add role name as a separate attribute (don't overwrite the ForeignKey)
                    user.role_name = payload.get('role', 'PATIENT')
                    request.user = user
                except User.DoesNotExist:
                    request.user = AnonymousUser()
            else:
                request.user = AnonymousUser()
                
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            request.user = AnonymousUser()