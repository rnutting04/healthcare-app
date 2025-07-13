import jwt
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

class JWTAuthenticationMiddleware:
    """Middleware to validate JWT tokens and ensure admin role"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = [
            '/static/',
            '/admin/login/',
            '/health/',
        ]
    
    def __call__(self, request):
        # Skip authentication for exempt paths
        if any(request.path.startswith(path) for path in self.exempt_paths):
            return self.get_response(request)
        
        # Get token from cookie or header
        token = request.COOKIES.get('access_token')
        if not token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            # For AJAX/API requests, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return JsonResponse({'error': 'Authentication required'}, status=401)
            # For regular page requests, redirect to login with next parameter
            login_url = f'/login/?next={quote(request.get_full_path())}'
            return HttpResponseRedirect(login_url)
        
        try:
            # Decode the JWT token
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Check if user has admin role
            if payload.get('role') != 'ADMIN':
                return JsonResponse({'error': 'Admin access required'}, status=403)
            
            # Attach user data to request
            request.user_data = payload
            
            # Try to fetch full user data from database service
            try:
                from .services import DatabaseService
                user_id = payload.get('user_id')
                if user_id:
                    full_user_data = DatabaseService.get_user(user_id)
                    # Merge the full user data with the JWT payload
                    request.user_data = {**payload, **full_user_data}
            except Exception as e:
                logger.warning(f"Could not fetch full user data: {str(e)}")
                # Continue with just the JWT payload data
            
        except jwt.ExpiredSignatureError:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return JsonResponse({'error': 'Token has expired'}, status=401)
            login_url = f'/login/?next={quote(request.get_full_path())}'
            return HttpResponseRedirect(login_url)
        except jwt.InvalidTokenError:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return JsonResponse({'error': 'Invalid token'}, status=401)
            login_url = f'/login/?next={quote(request.get_full_path())}'
            return HttpResponseRedirect(login_url)
        
        response = self.get_response(request)
        return response