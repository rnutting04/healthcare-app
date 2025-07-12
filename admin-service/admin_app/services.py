import requests
from django.conf import settings
import logging
from datetime import datetime

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
        return DatabaseService.make_request('GET', '/api/cancer-types/')
    
    @staticmethod
    def get_cancer_type(cancer_type_id):
        """Get specific cancer type"""
        return DatabaseService.make_request('GET', f'/api/cancer-types/{cancer_type_id}/')
    
    @staticmethod
    def create_cancer_type(data):
        """Create new cancer type"""
        return DatabaseService.make_request('POST', '/api/cancer-types/', data=data)
    
    @staticmethod
    def update_cancer_type(cancer_type_id, data):
        """Update cancer type"""
        return DatabaseService.make_request('PUT', f'/api/cancer-types/{cancer_type_id}/', data=data)
    
    @staticmethod
    def delete_cancer_type(cancer_type_id):
        """Delete cancer type"""
        return DatabaseService.make_request('DELETE', f'/api/cancer-types/{cancer_type_id}/')
    
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
    
    @staticmethod
    def check_all_services_health():
        """Check health status of all microservices"""
        services = {
            'auth-service': settings.AUTH_SERVICE_URL,
            'patient-service': settings.PATIENT_SERVICE_URL,
            'clinician-service': settings.CLINICIAN_SERVICE_URL,
            'database-service': settings.DATABASE_SERVICE_URL,
            'admin-service': 'http://admin-service:8005'  # Self check
        }
        
        health_status = {}
        
        for service_name, service_url in services.items():
            try:
                start_time = datetime.now()
                response = requests.get(
                    f"{service_url}/health/",
                    timeout=5
                )
                response_time = (datetime.now() - start_time).total_seconds() * 1000  # Convert to milliseconds
                
                if response.status_code == 200:
                    health_status[service_name] = {
                        'status': 'healthy',
                        'response_time': round(response_time, 2),
                        'details': response.json() if response.text else {}
                    }
                else:
                    health_status[service_name] = {
                        'status': 'unhealthy',
                        'response_time': round(response_time, 2),
                        'error': f'HTTP {response.status_code}'
                    }
            except requests.exceptions.Timeout:
                health_status[service_name] = {
                    'status': 'timeout',
                    'response_time': 5000,
                    'error': 'Request timed out'
                }
            except requests.exceptions.ConnectionError:
                health_status[service_name] = {
                    'status': 'down',
                    'response_time': 0,
                    'error': 'Connection refused'
                }
            except Exception as e:
                health_status[service_name] = {
                    'status': 'error',
                    'response_time': 0,
                    'error': str(e)
                }
        
        return health_status