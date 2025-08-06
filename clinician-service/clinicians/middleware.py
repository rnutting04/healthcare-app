import jwt
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
import requests
import json

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = ['/swagger/', '/redoc/', '/admin/', '/static/', '/clinician/static/', '/health/']
        self.api_paths = ['/api/']
        self.auth_service_url = settings.AUTH_SERVICE_URL

    def __call__(self, request):
        # Skip authentication for excluded paths
        for path in self.excluded_paths:
            if request.path.startswith(path):
                return self.get_response(request)
        
        # ALL endpoints require authentication, including health check
        # Determine if this is an API request
        is_api_request = any(request.path.startswith(path) for path in self.api_paths)
        
        if is_api_request:
            # API requests must have JWT in Authorization header
            return self._handle_api_auth(request)
        else:
            # HTML page requests - check for JWT in cookies or localStorage
            return self._handle_page_auth(request)
    
    def _handle_api_auth(self, request):
        """Handle JWT authentication for API requests"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Authorization header missing or invalid'}, status=401)
        
        token = auth_header.split(' ')[1]
        
        # Verify token with auth service
        try:
            verify_response = requests.get(
                f"{self.auth_service_url}/api/auth/verify/",
                headers={'Authorization': f'Bearer {token}'},
                timeout=5
            )
            
            if verify_response.status_code == 200:
                user_data = verify_response.json()
                request.user_id = user_data['user']['id']
                request.user_email = user_data['user']['email']
                request.user_role = user_data['user']['role_name']
                request.user_data = user_data['user']  # Add full user data
                
                # Check if user is a clinician or admin
                if request.user_role not in ['CLINICIAN', 'ADMIN']:
                    return JsonResponse({'error': 'Access denied. Clinicians only.'}, status=403)
                
                return self.get_response(request)
            else:
                return JsonResponse({'error': 'Invalid or expired token'}, status=401)
                
        except requests.RequestException as e:
            return JsonResponse({'error': f'Authentication service unavailable: {str(e)}'}, status=503)
    
    def _handle_page_auth(self, request):
        """Handle authentication for HTML page requests"""
        # Check for JWT token in cookies (for server-side rendering)
        token = request.COOKIES.get('access_token')
        
        if not token:
            # No token - redirect to login
            login_url = '/login/'
            next_url = request.get_full_path()
            return HttpResponseRedirect(f"{login_url}?next={next_url}")
        
        # Verify token with auth service
        try:
            verify_response = requests.get(
                f"{self.auth_service_url}/api/auth/verify/",
                headers={'Authorization': f'Bearer {token}'},
                timeout=5
            )
            
            if verify_response.status_code == 200:
                user_data = verify_response.json()
                request.user_id = user_data['user']['id']
                request.user_email = user_data['user']['email']
                request.user_role = user_data['user']['role_name']
                
                # Check if user is a clinician or admin
                if request.user_role not in ['CLINICIAN', 'ADMIN']:
                    return HttpResponseRedirect('/login/?error=unauthorized')
                
                # Add user data to request for templates
                request.user_data = user_data['user']
                
                return self.get_response(request)
            else:
                # Invalid token - redirect to login
                return HttpResponseRedirect('/login/?error=session_expired')
                
        except requests.RequestException:
            # Auth service unavailable
            return JsonResponse({'error': 'Authentication service unavailable'}, status=503)