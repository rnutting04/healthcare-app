from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Patient, Appointment, MedicalRecord, Prescription, Language
from .serializers import (
    PatientSerializer, AppointmentSerializer, 
    MedicalRecordSerializer, PrescriptionSerializer,
    PatientDashboardSerializer, LanguageSerializer
)
import requests
from django.conf import settings

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    
    def get_queryset(self):
        # Patients can only see their own data, admins can see all
        if hasattr(self.request, 'user_role'):
            if self.request.user_role == 'PATIENT':
                return self.queryset.filter(user_id=self.request.user_id)
        return self.queryset
    
    def create(self, request):
        # Create patient profile when user registers
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
            # Use current time if date_joined not available
            from django.utils import timezone
            data['created_at'] = timezone.now()
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        # Get current patient's profile
        patient = get_object_or_404(Patient, user_id=request.user_id)
        serializer = self.get_serializer(patient)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        # Get patient dashboard data
        try:
            patient = Patient.objects.get(user_id=request.user_id)
            serializer = PatientDashboardSerializer(patient)
            # Add user data from JWT token to the response
            dashboard_data = serializer.data
            dashboard_data['first_name'] = request.user_data.get('first_name', 'Patient')
            dashboard_data['last_name'] = request.user_data.get('last_name', '')
            dashboard_data['email'] = request.user_data.get('email', '')
            return Response(dashboard_data)
        except Patient.DoesNotExist:
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

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    
    def get_queryset(self):
        # Filter appointments based on user role
        if hasattr(self.request, 'user_role'):
            if self.request.user_role == 'PATIENT':
                patient = get_object_or_404(Patient, user_id=self.request.user_id)
                return self.queryset.filter(patient=patient)
        return self.queryset
    
    def create(self, request):
        # Patients create their own appointments
        patient = get_object_or_404(Patient, user_id=request.user_id)
        data = request.data.copy()
        data['patient'] = patient.id
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            
            # Notify database service about new appointment
            self._notify_database_service('appointment_created', serializer.data)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        
        # Check if patient owns the appointment
        if hasattr(request, 'user_role') and request.user_role == 'PATIENT':
            patient = get_object_or_404(Patient, user_id=request.user_id)
            if appointment.patient != patient:
                return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        appointment.status = 'CANCELLED'
        appointment.save()
        
        # Notify database service
        self._notify_database_service('appointment_cancelled', {'appointment_id': appointment.id})
        
        return Response({'message': 'Appointment cancelled successfully'})
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        # Get upcoming appointments
        patient = get_object_or_404(Patient, user_id=request.user_id)
        appointments = self.queryset.filter(
            patient=patient,
            appointment_date__gte=timezone.now(),
            status__in=['SCHEDULED', 'CONFIRMED']
        ).order_by('appointment_date')
        
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
    
    def _notify_database_service(self, event_type, data):
        try:
            headers = {
                'X-Service-Token': getattr(settings, 'DATABASE_SERVICE_TOKEN', 'db-service-secret-token')
            }
            requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/events/",
                json={
                    'event_type': event_type,
                    'service': 'patient-service',
                    'data': data
                },
                headers=headers
            )
        except:
            pass

class MedicalRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MedicalRecord.objects.all()
    serializer_class = MedicalRecordSerializer
    
    def get_queryset(self):
        # Patients can only see their own records
        if hasattr(self.request, 'user_role'):
            if self.request.user_role == 'PATIENT':
                patient = get_object_or_404(Patient, user_id=self.request.user_id)
                return self.queryset.filter(patient=patient)
        return self.queryset
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        # Get records filtered by type
        patient = get_object_or_404(Patient, user_id=request.user_id)
        record_type = request.query_params.get('type')
        
        records = self.queryset.filter(patient=patient)
        if record_type:
            records = records.filter(record_type=record_type)
        
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)

class PrescriptionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    
    def get_queryset(self):
        # Patients can only see their own prescriptions
        if hasattr(self.request, 'user_role'):
            if self.request.user_role == 'PATIENT':
                patient = get_object_or_404(Patient, user_id=request.user_id)
                return self.queryset.filter(patient=patient)
        return self.queryset
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        # Get active prescriptions
        patient = get_object_or_404(Patient, user_id=request.user_id)
        prescriptions = self.queryset.filter(
            patient=patient,
            is_active=True,
            end_date__gte=timezone.now().date()
        )
        
        serializer = self.get_serializer(prescriptions, many=True)
        return Response(serializer.data)

class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Language.objects.filter(is_active=True)
    serializer_class = LanguageSerializer
    permission_classes = []  # Allow anyone to view languages