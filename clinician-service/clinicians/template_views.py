from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from .services import DatabaseService
import logging

logger = logging.getLogger(__name__)


class ClinicianDashboardView(View):
    """Dashboard view for clinicians"""
    
    def get(self, request):
        """Render clinician dashboard"""
        try:
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            
            # Prepare context (stub data for now)
            context = {
                'user': request.user_data,
                'clinician': clinician,
                'stats': {
                    'total_patients': 0,
                    'today_appointments': 0,
                    'pending_appointments': 0,
                    'completed_appointments': 0
                },
                'upcoming_appointments': [],
                'recent_patients': [],
                'notifications': []
            }
            
            return render(request, 'clinician_dashboard.html', context)
            
        except Exception as e:
            logger.error(f"Failed to load dashboard: {e}")
            return render(request, 'clinician_dashboard.html', {
                'error': 'Failed to load dashboard data'
            })


class PatientDashboardView(View):
    """Dashboard view for a specific patient"""
    
    def get(self, request, patient_id):
        """Render patient dashboard"""
        try:
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            if not clinician:
                from django.http import HttpResponse
                return HttpResponse('Clinician profile not found', status=404)
            
            # Check if clinician is assigned to this patient
            # Get all patients assigned to this clinician
            assigned_patients = DatabaseService.get_clinician_patients(clinician['id'])
            patient_ids = [p['id'] for p in assigned_patients]
            
            if patient_id not in patient_ids:
                from django.http import HttpResponse
                return HttpResponse('You are not authorized to view this patient', status=403)
            
            # Get patient details
            patient = DatabaseService.get_patient(patient_id)
            if not patient:
                from django.http import HttpResponse
                return HttpResponse('Patient not found', status=404)
            
            # Get user info for patient
            if patient.get('user_id'):
                user = DatabaseService.get_user(patient['user_id'])
                if user:
                    patient['user'] = user
            
            # Log access
            DatabaseService.log_event('clinician_accessed_patient_dashboard', 'clinician-service', {
                'user_id': request.user_id,
                'clinician_id': clinician['id'],
                'patient_id': patient_id
            })
            
            # Get medical records for the patient
            medical_records_response = DatabaseService.get_patient_medical_records(patient_id)
            
            # Handle paginated response
            if isinstance(medical_records_response, dict) and 'results' in medical_records_response:
                medical_records = medical_records_response['results']
            else:
                medical_records = medical_records_response
            
            logger.info(f"Medical records for patient {patient_id}: {len(medical_records)} records found")
            
            # Prepare context for template
            context = {
                'user': request.user_data,
                'clinician': clinician,
                'patient': patient,
                'medical_records': medical_records,
                'prescriptions': [],    # Stub - will be implemented later
                'appointments': [],     # Stub - will be implemented later
                'recent_activity': []   # Stub - will be implemented later
            }
            
            return render(request, 'patient_dashboard.html', context)
            
        except Exception as e:
            logger.error(f"Failed to load patient dashboard: {e}")
            from django.http import HttpResponse
            return HttpResponse(f'Failed to load patient dashboard: {str(e)}', status=500)


class AddMedicalRecordView(View):
    """View for adding medical records"""
    
    def get(self, request, patient_id):
        """Render add medical record form"""
        try:
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            if not clinician:
                from django.http import HttpResponse
                return HttpResponse('Clinician profile not found', status=404)
            
            # Check if clinician is assigned to this patient
            assigned_patients = DatabaseService.get_clinician_patients(clinician['id'])
            patient_ids = [p['id'] for p in assigned_patients]
            
            if patient_id not in patient_ids:
                from django.http import HttpResponse
                return HttpResponse('You are not authorized to add records for this patient', status=403)
            
            # Get patient details
            patient = DatabaseService.get_patient(patient_id)
            if not patient:
                from django.http import HttpResponse
                return HttpResponse('Patient not found', status=404)
            
            # Get user info for patient
            if patient.get('user_id'):
                user = DatabaseService.get_user(patient['user_id'])
                if user:
                    patient['user'] = user
            
            # Get medical record types
            medical_record_types = DatabaseService.get_medical_record_types()
            
            context = {
                'user': request.user_data,
                'patient': patient,
                'medical_record_types': medical_record_types
            }
            
            return render(request, 'add_medical_record.html', context)
            
        except Exception as e:
            logger.error(f"Failed to load add medical record page: {e}")
            from django.http import HttpResponse
            return HttpResponse(f'Failed to load add medical record page: {str(e)}', status=500)
    
    def post(self, request, patient_id):
        """Handle medical record upload"""
        try:
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            if not clinician:
                from django.http import HttpResponse
                return HttpResponse('Clinician profile not found', status=404)
            
            # Check if clinician is assigned to this patient
            assigned_patients = DatabaseService.get_clinician_patients(clinician['id'])
            patient_ids = [p['id'] for p in assigned_patients]
            
            if patient_id not in patient_ids:
                from django.http import HttpResponse
                return HttpResponse('You are not authorized to add records for this patient', status=403)
            
            # Get form data
            record_type_name = request.POST.get('recordType')
            uploaded_file = request.FILES.get('document')
            
            if not record_type_name or not uploaded_file:
                from django.http import HttpResponse
                return HttpResponse('Missing required fields', status=400)
            
            # Get medical record type ID from name
            medical_record_types = DatabaseService.get_medical_record_types()
            record_type_id = None
            for record_type in medical_record_types:
                if record_type['type_name'] == record_type_name:
                    record_type_id = record_type['id']
                    break
            
            if not record_type_id:
                from django.http import HttpResponse
                return HttpResponse('Invalid record type', status=400)
            
            # Call file-service to upload the medical record
            import requests
            from django.conf import settings
            
            # Prepare the multipart form data
            files = {'file': (uploaded_file.name, uploaded_file, uploaded_file.content_type)}
            data = {
                'patient_id': patient_id,
                'medical_record_type_id': record_type_id
            }
            
            # Get JWT token from request
            auth_header = request.headers.get('Authorization', '')
            if not auth_header:
                # Try to get from cookie if not in header
                jwt_token = request.COOKIES.get('access_token', '')
                if jwt_token:
                    auth_header = f'Bearer {jwt_token}'
            
            headers = {}
            if auth_header:
                headers['Authorization'] = auth_header
            
            # Make request to file-service
            response = requests.post(
                f"{settings.FILE_SERVICE_URL}/api/files/upload/medical-record",
                files=files,
                data=data,
                headers=headers
            )
            
            if response.status_code == 201:
                # Success - redirect to patient dashboard
                return redirect('patient-dashboard-template', patient_id=patient_id)
            else:
                # Handle error
                error_msg = 'Failed to upload medical record'
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_msg)
                except:
                    pass
                
                from django.http import HttpResponse
                return HttpResponse(error_msg, status=response.status_code)
                
        except Exception as e:
            logger.error(f"Failed to upload medical record: {e}")
            from django.http import HttpResponse
            return HttpResponse(f'Failed to upload medical record: {str(e)}', status=500)