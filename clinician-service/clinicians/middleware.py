import jwt
from django.conf import settings
from django.http import JsonResponse
import requests

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = ['/health/', '/swagger/', '/redoc/', '/admin/']

    def __call__(self, request):
        # Skip authentication for excluded paths
        for path in self.excluded_paths:
            if request.path.startswith(path):
                return self.get_response(request)
        
        # Extract token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Authorization header missing or invalid'}, status=401)
        
        token = auth_header.split(' ')[1]
        
        try:
            # Decode JWT token
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            
            # Add user info to request
            request.user_id = payload.get('user_id')
            request.user_email = payload.get('email')
            request.user_role = payload.get('role')
            
            # Check if user is a clinician or admin
            if request.user_role not in ['CLINICIAN', 'ADMIN']:
                return JsonResponse({'error': 'Access denied. Clinicians only.'}, status=403)
            
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=401)
        
        response = self.get_response(request)
        return response