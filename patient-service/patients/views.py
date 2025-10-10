from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
import logging
from .services import DatabaseService
from .serializers import (
    PatientSerializer, AppointmentSerializer, 
    MedicalRecordSerializer, PrescriptionSerializer,
    PatientDashboardSerializer, LanguageSerializer,
    ChatSessionSerializer, ChatMessageSerializer
)

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
            # Debug logging
            logger.info(f"Dashboard request - user_id: {getattr(request, 'user_id', 'None')}")
            logger.info(f"Dashboard request - user_data type: {type(getattr(request, 'user_data', None))}")
            logger.info(f"Dashboard request - user_data: {getattr(request, 'user_data', 'None')}")
            
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            
            if patient:
                # Get upcoming appointments
                appointments = DatabaseService.get_upcoming_appointments(patient['id'])
                
                # Get recent medical records
                try:
                    medical_records = DatabaseService.get_medical_records({
                        'patient_id': patient['id']
                    })
                    if isinstance(medical_records, list):
                        recent_records = sorted(medical_records, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
                    else:
                        logger.warning(f"Medical records returned non-list: {type(medical_records)}")
                        recent_records = []
                except Exception as e:
                    logger.warning(f"Could not fetch medical records: {e}")
                    recent_records = []
                
                # Get active prescriptions
                active_prescriptions = DatabaseService.get_active_prescriptions(patient['id'])
                
                # Ensure user_data is a dict
                user_data = getattr(request, 'user_data', {})
                if not isinstance(user_data, dict):
                    user_data = {}
                
                dashboard_data = {
                    'user_id': request.user_id,
                    'first_name': user_data.get('first_name', 'Patient'),
                    'last_name': user_data.get('last_name', ''),
                    'email': user_data.get('email', ''),
                    'patient_profile': patient,
                    'upcoming_appointments': appointments[:5],
                    'recent_records': recent_records,
                    'active_prescriptions': active_prescriptions
                }
                return Response(dashboard_data)
            else:
                # Return basic user data if patient profile doesn't exist yet
                # Ensure user_data is a dict
                user_data = getattr(request, 'user_data', {})
                if not isinstance(user_data, dict):
                    user_data = {}
                    
                return Response({
                    'user_id': request.user_id,
                    'first_name': user_data.get('first_name', 'Patient'),
                    'last_name': user_data.get('last_name', ''),
                    'email': user_data.get('email', ''),
                    'upcoming_appointments': [],
                    'recent_records': [],
                    'active_prescriptions': []
                })
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            logger.error(f"Error type: {type(e)}, Error details: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
    
    @action(detail=False, methods=['get'])
    def record_types(self, request):
        """Get all available medical record types"""
        record_types = DatabaseService.get_medical_record_types()
        return Response(record_types)
    
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
    


from django.conf import settings
from .rag_service import RAGService

class ChatViewSet(viewsets.ViewSet):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rag_service = RAGService()
        
    def get_patient(self, request):
        return DatabaseService.get_patient_by_user_id(request.user_id)

    @action(detail=False, methods=["post"])
    def start(self, request):
        patient = self.get_patient(request)
        session = DatabaseService.create_chat_session(patient['id'])

        return Response({
            "session": ChatSessionSerializer(session).data,
        })

    @action(detail=False, methods=['get'])
    def sessions(self, request):
        patient = self.get_patient(request)
        sessions = DatabaseService.get_chat_sessions_by_patient(patient['id'])
        serializer = ChatSessionSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def load(self, request):
        session_id = request.data.get("session_id")
        if not session_id:
            return Response({"error": "Session ID is required."}, status=400)

        patient = self.get_patient(request)
        session, messages = DatabaseService.get_session_and_messages(session_id, patient['id'])
        if not session:
            return Response({"error": "Session not found."}, status=404)
        return Response({
            "session": ChatSessionSerializer(session).data,
            "messages": ChatMessageSerializer(messages, many=True).data,
            "suggestions": ChatSessionSerializer(session).data.get('suggestions')
        })

   
    @action(detail=False, methods=["post"])
    def message(self, request):
        user_message = (request.data.get("message") or "").strip()
        session_id = request.data.get("session_id")


        if not user_message:
            return Response({"error": "Message is required"}, status=400)

        patient = self.get_patient(request)
        if not patient:
            return Response({"error": "Patient not found"}, status=404)
        preferred_language = (patient.get("preferred_language") or "English").strip()

        if session_id:
            session = DatabaseService.get_chat_session_by_id_and_patient(session_id, patient["id"])
            if not session:
                return Response({"error": "Invalid session ID"}, status=400)
        else:
            session = DatabaseService.get_latest_chat_session(patient["id"])
            if not session:
                session = DatabaseService.create_chat_session(patient["id"])
                initialAssitantMessage = "Hello! I'm your medical assistant. I can help answer questions about your condition based on medical documents. How can I help you today?"
                DatabaseService.create_chat_message(session["id"], "assistant",initialAssitantMessage)
                
        messages = DatabaseService.get_messages_for_session(session["id"])
        chat_history = [{"role": "system", "content": (
            "You are a helpful assistant for a patient dashboard following NCCN guidelines. "
            f"Reply in patients preferred language {preferred_language}."
        )}]
        for msg in messages:
            chat_history.append({"role": msg.role, "content": msg.content})

        chat_history.append({"role": "user", "content": user_message})

        try:
            rough_token_count = sum(len(m["content"]) for m in chat_history) // 4
            if rough_token_count > getattr(settings, "OPENAI_MAX_TOKENS_PER_CHUNK", 8000):
                session = DatabaseService.create_chat_session(patient["id"])
                chat_history = [
                    {"role": "system", "content": (
                        "You are a helpful assistant for a patient dashboard following NCCN guidelines. "
                        f"Reply in {preferred_language}."
                    )},
                    {"role": "user", "content": user_message},
                ]
        except Exception as e:
            logger.warning(f"Token guard calculation failed, proceeding anyway: {e}")

        DatabaseService.create_chat_message(session["id"], "user", user_message)

        # Cancer type + auth for RAG
        try:
            main_cancer_type, sub_cancer_type = self._get_cancer_type(patient)
        except Exception:
            main_cancer_type, sub_cancer_type = self.rag_service.FALLBACK_CANCER_TYPE  # 'uterine'

        auth_token = (request.META.get("HTTP_AUTHORIZATION", "") or "").replace("Bearer ", "")
        if not auth_token:
            return Response({"error": "Authentication required"}, status=401)

        #Call RAG (LangChain) service
        logger.info(patient)
        try:
            result = self.rag_service.query_with_context(
                query=user_message,
                language=patient.get("preferred_language_code", "en"),
                cancer_type=main_cancer_type,
                auth_token=auth_token,
                session_id=session["id"],
                chat_history=chat_history,
            )
        except Exception as e:
            logger.exception("Exception calling RAG service")
            return Response({"error": "Failed to generate response", "details": str(e)}, status=500)

        # Normalize result
        if not isinstance(result, dict):
            logger.error(f"RAG returned non-dict: {type(result)} - {result}")
            result = {
                "success": False,
                "response": "I apologize, but I encountered an error processing your request."
            }

        if result.get("success"):
            reply = (result.get("answer") or result.get("response") or "").strip()
        else:
            reply = (result.get("response") or "I’m sorry—I couldn’t process that right now.").strip()

        # Persist assistant reply
        DatabaseService.create_chat_message(session["id"], "assistant", reply)

        try:
            if not session.get("title") or session["title"].strip() == "New Chat":
                generated_title = (user_message[:25] or "Conversation").strip()
                DatabaseService.update_session_title(session["id"], generated_title)
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")


        return Response(
            {
                "response": reply,
                "session_id": session["id"],
            },
            status=status.HTTP_200_OK,
        )
    
    @action(detail=True, methods=["delete"])
    def delete(self, request, pk=None):
        patient = self.get_patient(request)
        success = DatabaseService.delete_chat_session(pk, patient['id'])
        if success:
            return Response({"message": "Session deleted."})
        return Response({"error": "Delete failed or session not found."}, status=400)

    @action(detail=False, methods=['get'])
    def context(self, request):
        """Get the current cancer type context for the patient"""
        try:
            patient = self.get_patient(request)
            logger.info(patient)
            if not patient:
                return Response(
                    {'error': 'Patient profile not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            main_cancer_type, sub_cancer_type = self._get_cancer_type(patient)
            
            preferred_language = patient.get('preferred_language', 'English')
            
            return Response({
                'language': preferred_language,
                'main_cancer_type': main_cancer_type,
                'sub_cancer_type': sub_cancer_type,
                'is_fallback': main_cancer_type == 'Not Assigned' 
            })
            
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return Response(
                {'error': 'Unable to determine context'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def _get_cancer_type(self, patient: dict) -> str:
        """Extract cancer type from patient data with fallback"""
        # Try to get cancer type from patient profile
        assignment = patient.get('assignment')
        sub_cancer_type = assignment['cancer_subtype_name']
        main_cancer_type = assignment['cancer_type_name']
        
        logger.info(assignment)
        
        if not sub_cancer_type or not main_cancer_type:
            # Try to get from cancer_type_detail
            cancer_detail = patient.get('cancer_type_detail', {})
            sub_cancer_type = cancer_detail.get('name', '').strip()
            main_cancer_type = cancer_detail.get('name', '').strip()
        
        if not sub_cancer_type or not main_cancer_type:
            # Default to uterine if not found or empty
            sub_cancer_type = 'Not Assigned'
            main_cancer_type = 'Not Assigned'
        

        return main_cancer_type, sub_cancer_type
    
