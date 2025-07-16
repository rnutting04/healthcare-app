import jwt
import requests
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger('embedding')


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate requests using JWT tokens or service tokens.
    """
    
    def process_request(self, request):
        # Skip authentication for health check endpoint
        if request.path == '/health/':
            return None
            
        # Skip authentication for admin
        if request.path.startswith('/admin/'):
            return None
            
        # Check for service token authentication
        service_token = request.headers.get('X-Service-Token')
        if service_token == 'db-service-secret-token':
            request.is_authenticated = True
            request.user_type = 'service'
            return None
            
        # Check for JWT authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JsonResponse({'error': 'Authentication required'}, status=401)
            
        try:
            # Extract token from "Bearer <token>" format
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            
            # Verify token with auth service
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{settings.AUTH_SERVICE_URL}/api/auth/verify/",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('valid'):
                    user_data = data.get('user', {})
                    request.is_authenticated = True
                    request.user_id = user_data.get('id')
                    request.user_type = user_data.get('role_name')
                    request.email = user_data.get('email')
                    return None
                else:
                    return JsonResponse({'error': 'Invalid token'}, status=401)
            else:
                return JsonResponse({'error': 'Invalid token'}, status=401)
                
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=401)
        except requests.RequestException as e:
            logger.error(f"Error verifying token with auth service: {str(e)}")
            return JsonResponse({'error': 'Authentication service unavailable'}, status=503)
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return JsonResponse({'error': 'Authentication failed'}, status=401)