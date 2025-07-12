import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service to communicate with database-service"""
    
    @staticmethod
    def make_request(method, endpoint, data=None, params=None, headers=None):
        """Make HTTP request to database service"""
        url = f"{settings.DATABASE_SERVICE_URL}{endpoint}"
        
        # If no headers provided, create empty dict
        if headers is None:
            headers = {}
        
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
            logger.error(f"Database service request failed: {str(e)}")
            raise Exception(f"Database service error: {str(e)}")
    
    # Cancer Type Management
    @staticmethod
    def get_cancer_types():
        """Get all cancer types"""
        return DatabaseService.make_request('GET', '/api/db/cancer-types/')
    
    @staticmethod
    def get_cancer_type(cancer_type_id):
        """Get specific cancer type"""
        return DatabaseService.make_request('GET', f'/api/db/cancer-types/{cancer_type_id}/')
    
    @staticmethod
    def create_cancer_type(data):
        """Create new cancer type"""
        return DatabaseService.make_request('POST', '/api/db/cancer-types/', data=data)
    
    @staticmethod
    def update_cancer_type(cancer_type_id, data):
        """Update cancer type"""
        return DatabaseService.make_request('PUT', f'/api/db/cancer-types/{cancer_type_id}/', data=data)
    
    @staticmethod
    def delete_cancer_type(cancer_type_id):
        """Delete cancer type"""
        return DatabaseService.make_request('DELETE', f'/api/db/cancer-types/{cancer_type_id}/')
    
    # Cancer Subtype Management
    @staticmethod
    def get_cancer_subtypes(cancer_type_id=None):
        """Get cancer subtypes, optionally filtered by cancer type"""
        params = {'cancer_type_id': cancer_type_id} if cancer_type_id else None
        return DatabaseService.make_request('GET', '/api/cancer-subtypes/', params=params)
    
    @staticmethod
    def get_cancer_subtype(subtype_id):
        """Get specific cancer subtype"""
        return DatabaseService.make_request('GET', f'/api/cancer-subtypes/{subtype_id}/')
    
    @staticmethod
    def create_cancer_subtype(data):
        """Create new cancer subtype"""
        return DatabaseService.make_request('POST', '/api/cancer-subtypes/', data=data)
    
    @staticmethod
    def update_cancer_subtype(subtype_id, data):
        """Update cancer subtype"""
        return DatabaseService.make_request('PUT', f'/api/cancer-subtypes/{subtype_id}/', data=data)
    
    @staticmethod
    def delete_cancer_subtype(subtype_id):
        """Delete cancer subtype"""
        return DatabaseService.make_request('DELETE', f'/api/cancer-subtypes/{subtype_id}/')
    
    # User Management
    @staticmethod
    def get_all_users(role=None, is_active=None):
        """Get all users with optional filters"""
        params = {}
        if role:
            params['role'] = role
        if is_active is not None:
            params['is_active'] = is_active
        return DatabaseService.make_request('GET', '/api/users/', params=params)
    
    @staticmethod
    def get_user(user_id):
        """Get specific user"""
        return DatabaseService.make_request('GET', f'/api/users/{user_id}/')
    
    @staticmethod
    def update_user_status(user_id, is_active):
        """Update user active status (revoke/restore permissions)"""
        data = {'is_active': is_active}
        return DatabaseService.make_request('PATCH', f'/api/users/{user_id}/status/', data=data)
    
    @staticmethod
    def get_user_statistics():
        """Get user statistics"""
        return DatabaseService.make_request('GET', '/api/users/statistics/')
    
    @staticmethod
    def get_patient_by_user(user_id):
        """Get patient data by user ID"""
        return DatabaseService.make_request('GET', '/api/patients/by_user/', params={'user_id': user_id})
    
    @staticmethod
    def update_patient(patient_id, data):
        """Update patient information"""
        return DatabaseService.make_request('PATCH', f'/api/patients/{patient_id}/', data=data)