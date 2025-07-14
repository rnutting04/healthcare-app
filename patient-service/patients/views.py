from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from .services import DatabaseService
from .serializers import (
    PatientSerializer, AppointmentSerializer, 
    MedicalRecordSerializer, PrescriptionSerializer,
    PatientDashboardSerializer, LanguageSerializer
)
import logging

logger = logging.getLogger(__name__)


class PatientViewSet(viewsets.ViewSet):
    """Patient ViewSet using DatabaseService"""
    
    def list(self, request):
        """List patients - only accessible by admin"""
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            # Patients can only see their own data
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if patient:
                return Response([patient])
            return Response([])
        
        # Admin can see all patients - implement pagination if needed
        return Response({'error': 'Not implemented for admin'}, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    def retrieve(self, request, pk=None):
        """Get specific patient"""
        patient = DatabaseService.get_patient(pk)
        if not patient:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            if patient.get('user_id') != request.user_id:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        return Response(patient)
    
    def create(self, request):
        """Create patient profile when user registers"""
        data = request.data.copy()
        
        # Ensure user_id is set from the authenticated user
        if hasattr(request, 'user_id'):
            data['user_id'] = request.user_id
        else:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Set created_at from auth service's date_joined
        if hasattr(request, 'user_data') and 'date_joined' in request.user_data:
            data['created_at'] = request.user_data['date_joined']
        else:
            data['created_at'] = timezone.now().isoformat()
        
        try:
            patient = DatabaseService.create_patient(data)
            return Response(patient, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to create patient: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk=None):
        """Update patient profile (PUT)"""
        patient = DatabaseService.get_patient(pk)
        if not patient:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            if patient.get('user_id') != request.user_id:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            updated_patient = DatabaseService.update_patient(pk, request.data)
            return Response(updated_patient)
        except Exception as e:
            logger.error(f"Failed to update patient: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        """Partially update patient profile (PATCH)"""
        patient = DatabaseService.get_patient(pk)
        if not patient:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            if patient.get('user_id') != request.user_id:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            updated_patient = DatabaseService.update_patient(pk, request.data)
            return Response(updated_patient)
        except Exception as e:
            logger.error(f"Failed to update patient: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current patient's profile"""
        patient = DatabaseService.get_patient_by_user_id(request.user_id)
        if not patient:
            return Response({'error': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(patient)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get patient dashboard data"""
        try:
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            
            if patient:
                # Get upcoming appointments
                appointments = DatabaseService.get_upcoming_appointments(patient['id'])
                
                # Get recent medical records
                medical_records = DatabaseService.get_medical_records({
                    'patient_id': patient['id']
                })
                recent_records = sorted(medical_records, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
                
                # Get active prescriptions
                active_prescriptions = DatabaseService.get_active_prescriptions(patient['id'])
                
                dashboard_data = {
                    'user_id': request.user_id,
                    'first_name': request.user_data.get('first_name', 'Patient'),
                    'last_name': request.user_data.get('last_name', ''),
                    'email': request.user_data.get('email', ''),
                    'patient_profile': patient,
                    'upcoming_appointments': appointments[:5],
                    'recent_records': recent_records,
                    'active_prescriptions': active_prescriptions
                }
                return Response(dashboard_data)
            else:
                # Return basic user data if patient profile doesn't exist yet
                return Response({
                    'user_id': request.user_id,
                    'first_name': request.user_data.get('first_name', 'Patient'),
                    'last_name': request.user_data.get('last_name', ''),
                    'email': request.user_data.get('email', ''),
                    'upcoming_appointments': [],
                    'recent_records': [],
                    'active_prescriptions': []
                })
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return Response({'error': 'Failed to load dashboard'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AppointmentViewSet(viewsets.ViewSet):
    """Appointment ViewSet using DatabaseService"""
    
    def list(self, request):
        """List appointments"""
        params = {}
        
        # Filter based on user role
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient:
                return Response([])
            params['patient_id'] = patient['id']
        
        # Add query parameters
        for param in ['status', 'start_date', 'end_date']:
            if param in request.query_params:
                params[param] = request.query_params[param]
        
        appointments = DatabaseService.get_appointments(params)
        return Response(appointments)
    
    def retrieve(self, request, pk=None):
        """Get specific appointment"""
        appointment = DatabaseService.get_appointment(pk)
        if not appointment:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient or appointment.get('patient') != patient['id']:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        return Response(appointment)
    
    def create(self, request):
        """Create appointment"""
        patient = DatabaseService.get_patient_by_user_id(request.user_id)
        if not patient:
            return Response({'error': 'Patient profile required'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data.copy()
        data['patient'] = patient['id']
        
        # Get clinician name if clinician_id is provided
        if 'clinician_id' in data:
            clinician = DatabaseService.get_clinician(data['clinician_id'])
            if clinician and 'user' in clinician:
                data['clinician_name'] = f"Dr. {clinician['user']['first_name']} {clinician['user']['last_name']}"
        
        try:
            appointment = DatabaseService.create_appointment(data)
            
            # Log event
            DatabaseService.log_event('appointment_created', 'patient-service', {
                'appointment_id': appointment['id'],
                'patient_id': patient['id'],
                'clinician_id': data.get('clinician_id')
            })
            
            return Response(appointment, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to create appointment: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk=None):
        """Update appointment (PUT)"""
        appointment = DatabaseService.get_appointment(pk)
        if not appointment:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient or appointment.get('patient') != patient['id']:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            updated_appointment = DatabaseService.update_appointment(pk, request.data)
            
            # Log event if status changed
            if 'status' in request.data:
                DatabaseService.log_event('appointment_status_changed', 'patient-service', {
                    'appointment_id': pk,
                    'old_status': appointment.get('status'),
                    'new_status': request.data['status']
                })
            
            return Response(updated_appointment)
        except Exception as e:
            logger.error(f"Failed to update appointment: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        """Partially update appointment (PATCH)"""
        appointment = DatabaseService.get_appointment(pk)
        if not appointment:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient or appointment.get('patient') != patient['id']:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            updated_appointment = DatabaseService.update_appointment(pk, request.data)
            
            # Log event if status changed
            if 'status' in request.data:
                DatabaseService.log_event('appointment_status_changed', 'patient-service', {
                    'appointment_id': pk,
                    'old_status': appointment.get('status'),
                    'new_status': request.data['status']
                })
            
            return Response(updated_appointment)
        except Exception as e:
            logger.error(f"Failed to update appointment: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming appointments"""
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient:
                return Response([])
            appointments = DatabaseService.get_upcoming_appointments(patient['id'])
        else:
            appointments = DatabaseService.get_upcoming_appointments()
        
        return Response(appointments)
    
    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        """Get available appointment slots"""
        clinician_id = request.query_params.get('clinician_id')
        date = request.query_params.get('date', timezone.now().date())
        
        if not clinician_id:
            return Response({'error': 'clinician_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # This is a simplified implementation
        # In production, this would check against existing appointments
        slots = []
        start_hour = 9
        end_hour = 17
        
        for hour in range(start_hour, end_hour):
            slots.append(f"{hour}:00")
            slots.append(f"{hour}:30")
        
        return Response({'date': date, 'available_slots': slots})


class MedicalRecordViewSet(viewsets.ViewSet):
    """Medical Record ViewSet using DatabaseService"""
    
    def list(self, request):
        """List medical records"""
        params = {}
        
        # Filter based on user role
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient:
                return Response([])
            params['patient_id'] = patient['id']
        
        # Add query parameters
        if 'record_type' in request.query_params:
            params['record_type'] = request.query_params['record_type']
        
        records = DatabaseService.get_medical_records(params)
        return Response(records)
    
    def retrieve(self, request, pk=None):
        """Get specific medical record"""
        record = DatabaseService.get_medical_record(pk)
        if not record:
            return Response({'error': 'Medical record not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient or record.get('patient') != patient['id']:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        return Response(record)


class PrescriptionViewSet(viewsets.ViewSet):
    """Prescription ViewSet using DatabaseService"""
    
    def list(self, request):
        """List prescriptions"""
        params = {}
        
        # Filter based on user role
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient:
                return Response([])
            params['patient_id'] = patient['id']
        
        # Add query parameters
        if 'is_active' in request.query_params:
            params['is_active'] = request.query_params['is_active'].lower() == 'true'
        
        prescriptions = DatabaseService.get_prescriptions(params)
        return Response(prescriptions)
    
    def retrieve(self, request, pk=None):
        """Get specific prescription"""
        prescription = DatabaseService.get_prescription(pk)
        if not prescription:
            return Response({'error': 'Prescription not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient or prescription.get('patient') != patient['id']:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        return Response(prescription)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active prescriptions"""
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            if not patient:
                return Response([])
            prescriptions = DatabaseService.get_active_prescriptions(patient['id'])
            return Response(prescriptions)
        
        return Response({'error': 'Patient role required'}, status=status.HTTP_403_FORBIDDEN)


class LanguageViewSet(viewsets.ViewSet):
    """Language ViewSet using DatabaseService"""
    
    def list(self, request):
        """List all active languages"""
        languages = DatabaseService.get_languages()
        return Response(languages)
    
    def retrieve(self, request, pk=None):
        """Get specific language"""
        language = DatabaseService.get_language(pk)
        if not language:
            return Response({'error': 'Language not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(language)