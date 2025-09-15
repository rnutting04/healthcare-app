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
    def get_user(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            return DatabaseService.make_request('GET', f'/api/users/{user_id}/')
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            return DatabaseService.make_request('GET', '/api/users/by_email/', params={'email': email})
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None
    
    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user with clinician role"""
        # Ensure role is set to CLINICIAN
        user_data['role'] = 'CLINICIAN'
        return DatabaseService.make_request('POST', '/api/users/', data=user_data)
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        try:
            return DatabaseService.make_request('POST', '/api/users/authenticate/', data={
                'email': email,
                'password': password
            })
        except Exception as e:
            logger.error(f"Failed to authenticate user: {e}")
            return None
    
    # Clinician operations
    @staticmethod
    def get_clinician_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Get clinician by user ID"""
        try:
            return DatabaseService.make_request('GET', '/api/clinicians/by_user/', params={'user_id': user_id})
        except Exception as e:
            logger.error(f"Failed to get clinician by user ID: {e}")
            return None
    
    @staticmethod
    def get_clinician(clinician_id: int) -> Optional[Dict[str, Any]]:
        """Get clinician by ID"""
        try:
            return DatabaseService.make_request('GET', f'/api/clinicians/{clinician_id}/')
        except Exception as e:
            logger.error(f"Failed to get clinician: {e}")
            return None
    
    @staticmethod
    def create_clinician(clinician_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new clinician profile"""
        return DatabaseService.make_request('POST', '/api/clinicians/', data=clinician_data)
    
    @staticmethod
    def update_clinician(clinician_id: int, clinician_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update clinician information"""
        return DatabaseService.make_request('PATCH', f'/api/clinicians/{clinician_id}/', data=clinician_data)
    
    # Patient operations for clinician dashboard
    @staticmethod
    def get_clinician_patients(clinician_id: int) -> List[Dict[str, Any]]:
        """Get patients assigned to a clinician"""
        try:
            return DatabaseService.make_request('GET', '/api/patients/by_clinician/', 
                                              params={'clinician_id': clinician_id})
        except Exception as e:
            logger.error(f"Failed to get clinician patients: {e}")
            return []
    
    @staticmethod
    def get_patient(patient_id: int) -> Optional[Dict[str, Any]]:
        """Get patient by ID"""
        try:
            return DatabaseService.make_request('GET', f'/api/patients/{patient_id}/')
        except Exception as e:
            logger.error(f"Failed to get patient: {e}")
            return None
    
    # Appointment operations for clinician dashboard
    @staticmethod
    def get_clinician_appointments(clinician_id: int, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get appointments for a clinician"""
        if params is None:
            params = {}
        params['clinician_id'] = clinician_id
        
        try:
            return DatabaseService.make_request('GET', '/api/appointments/', params=params)
        except Exception as e:
            logger.error(f"Failed to get clinician appointments: {e}")
            return []
    
    @staticmethod
    def get_upcoming_appointments_for_clinician(clinician_id: int) -> List[Dict[str, Any]]:
        """Get upcoming appointments for a clinician"""
        try:
            return DatabaseService.make_request('GET', '/api/appointments/upcoming/', 
                                              params={'clinician_id': clinician_id})
        except Exception as e:
            logger.error(f"Failed to get upcoming appointments: {e}")
            return []
    
    # Event logging
    @staticmethod
    def log_event(event_type: str, service: str, data: Dict[str, Any]) -> None:
        """Log an event to database service"""
        try:
            DatabaseService.make_request('POST', '/api/events/', data={
                'event_type': event_type,
                'service': service,
                'data': data
            })
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
    
    # Refresh token operations
    @staticmethod
    def create_refresh_token(user_id: int, token: str, expires_at: str) -> Dict[str, Any]:
        """Create a refresh token"""
        return DatabaseService.make_request('POST', '/api/refresh-tokens/', data={
            'user_id': user_id,
            'token': token,
            'expires_at': expires_at
        })
    
    @staticmethod
    def get_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """Get refresh token by token value"""
        try:
            return DatabaseService.make_request('GET', '/api/refresh-tokens/by_token/', params={'token': token})
        except Exception as e:
            logger.error(f"Failed to get refresh token: {e}")
            return None
    
    @staticmethod
    def invalidate_refresh_token(token: str) -> None:
        """Invalidate a refresh token"""
        try:
            DatabaseService.make_request('POST', '/api/refresh-tokens/invalidate/', data={'token': token})
        except Exception as e:
            logger.error(f"Failed to invalidate refresh token: {e}")
    
    @staticmethod
    def invalidate_user_tokens(user_id: int) -> None:
        """Invalidate all refresh tokens for a user"""
        try:
            DatabaseService.make_request('POST', '/api/refresh-tokens/invalidate_user/', data={'user_id': user_id})
        except Exception as e:
            logger.error(f"Failed to invalidate user tokens: {e}")
    
    @staticmethod
    def get_medical_record_types() -> List[Dict[str, Any]]:
        """Get available medical record types"""
        try:
            return DatabaseService.make_request('GET', '/api/medical-record-types/')
        except Exception as e:
            logger.error(f"Failed to get medical record types: {e}")
            return []
    
    @staticmethod
    def get_patient_medical_records(patient_id: int) -> List[Dict[str, Any]]:
        """Get all medical records for a patient"""
        try:
            return DatabaseService.make_request('GET', '/api/medical-records/', params={'patient': patient_id})
        except Exception as e:
            logger.error(f"Failed to get patient medical records: {e}")
            return []