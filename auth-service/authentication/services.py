import requests
from django.conf import settings
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service class for communicating with database-service"""
    
    @staticmethod
    def make_request(method: str, endpoint: str, data: Optional[Dict] = None, 
                    params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to database service"""
        url = f"{settings.DATABASE_SERVICE_URL}{endpoint}"
        
        if headers is None:
            headers = {}
        
        # Add service authentication token
        headers['X-Service-Token'] = getattr(settings, 'DATABASE_SERVICE_TOKEN', 'db-service-secret-token')
        headers['Content-Type'] = 'application/json'
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Database service request failed: {e}")
            raise Exception(f"Database service error: {str(e)}")
    
    # User operations
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            return DatabaseService.make_request('GET', '/api/users/by_email/', params={'email': email})
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            return DatabaseService.make_request('GET', f'/api/users/{user_id}/')
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None
    
    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        return DatabaseService.make_request('POST', '/api/users/', data=user_data)
    
    @staticmethod
    def update_user(user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information"""
        return DatabaseService.make_request('PATCH', f'/api/users/{user_id}/', data=user_data)
    
    @staticmethod
    def get_user_statistics() -> Dict[str, Any]:
        """Get user statistics"""
        return DatabaseService.make_request('GET', '/api/users/statistics/')
    
    # RefreshToken operations
    @staticmethod
    def create_refresh_token(user_id: int, token: str, expires_at: str) -> Dict[str, Any]:
        """Create a new refresh token"""
        return DatabaseService.make_request('POST', '/api/refresh-tokens/create_token/', data={
            'user_id': user_id,
            'token': token,
            'expires_at': expires_at
        })
    
    @staticmethod
    def validate_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """Validate a refresh token"""
        try:
            return DatabaseService.make_request('GET', '/api/refresh-tokens/validate_token/', params={'token': token})
        except Exception as e:
            logger.error(f"Failed to validate refresh token: {e}")
            return None
    
    @staticmethod
    def invalidate_refresh_token(token: str) -> Dict[str, Any]:
        """Invalidate a refresh token"""
        return DatabaseService.make_request('POST', '/api/refresh-tokens/invalidate_token/', data={'token': token})
    
    @staticmethod
    def invalidate_user_tokens(user_id: int) -> Dict[str, Any]:
        """Invalidate all tokens for a user"""
        return DatabaseService.make_request('POST', '/api/refresh-tokens/invalidate_user_tokens/', data={'user_id': user_id})
    
    @staticmethod
    def cleanup_expired_tokens() -> Dict[str, Any]:
        """Cleanup expired tokens"""
        return DatabaseService.make_request('DELETE', '/api/refresh-tokens/cleanup_expired/')
    
    # Patient profile operations
    @staticmethod
    def create_patient_profile(patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create patient profile"""
        return DatabaseService.make_request('POST', '/api/patients/', data=patient_data)
    
    @staticmethod
    def get_patient_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Get patient profile by user ID"""
        try:
            return DatabaseService.make_request('GET', '/api/patients/by_user/', params={'user_id': user_id})
        except Exception as e:
            logger.error(f"Failed to get patient by user ID: {e}")
            return None
    
    # Role operations
    @staticmethod
    def get_roles() -> List[Dict[str, Any]]:
        """Get all roles"""
        try:
            response = DatabaseService.make_request('GET', '/api/roles/')
            return response if isinstance(response, list) else []
        except Exception as e:
            logger.error(f"Failed to get roles: {e}")
            return []
    
    @staticmethod
    def get_role_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Get role by name"""
        roles = DatabaseService.get_roles()
        for role in roles:
            if role.get('name') == name:
                return role
        return None