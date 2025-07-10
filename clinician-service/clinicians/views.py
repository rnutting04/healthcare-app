from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Clinician, Schedule, PatientAssignment, ClinicianAppointment, MedicalNote
from .serializers import (
    ClinicianSerializer, ScheduleSerializer, PatientAssignmentSerializer,
    ClinicianAppointmentSerializer, MedicalNoteSerializer, ClinicianDashboardSerializer
)
import requests
from django.conf import settings

class ClinicianViewSet(viewsets.ModelViewSet):
    queryset = Clinician.objects.all()
    serializer_class = ClinicianSerializer
    
    def get_queryset(self):
        # Clinicians can only see their own data, admins can see all
        if hasattr(self.request, 'user_role'):
            if self.request.user_role == 'CLINICIAN':
                return self.queryset.filter(user_id=self.request.user_id)
        return self.queryset
    
    def create(self, request):
        # Create clinician profile when user registers
        data = request.data.copy()
        data['user_id'] = request.user_id
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        # Get current clinician's profile
        clinician = get_object_or_404(Clinician, user_id=request.user_id)
        serializer = self.get_serializer(clinician)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        # Get clinician dashboard data
        clinician = get_object_or_404(Clinician, user_id=request.user_id)
        serializer = ClinicianDashboardSerializer(clinician)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        # Get available clinicians
        clinicians = self.queryset.filter(is_available=True)
        serializer = self.get_serializer(clinicians, many=True)
        return Response(serializer.data)

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    
    def get_queryset(self):
        # Filter schedules based on user role
        if hasattr(self.request, 'user_role'):
            if self.request.user_role == 'CLINICIAN':
                clinician = get_object_or_404(Clinician, user_id=self.request.user_id)
                return self.queryset.filter(clinician=clinician)
        return self.queryset
    
    def create(self, request):
        # Clinicians create their own schedules
        clinician = get_object_or_404(Clinician, user_id=request.user_id)
        data = request.data.copy()
        data['clinician'] = clinician.id
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PatientAssignmentViewSet(viewsets.ModelViewSet):
    queryset = PatientAssignment.objects.all()
    serializer_class = PatientAssignmentSerializer
    
    def get_queryset(self):
        # Filter patient assignments based on user role
        if hasattr(self.request, 'user_role'):
            if self.request.user_role == 'CLINICIAN':
                clinician = get_object_or_404(Clinician, user_id=self.request.user_id)
                return self.queryset.filter(clinician=clinician)
        return self.queryset
    
    def create(self, request):
        # Clinicians assign patients to themselves
        clinician = get_object_or_404(Clinician, user_id=request.user_id)
        data = request.data.copy()
        data['clinician'] = clinician.id
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            
            # Notify database service
            self._notify_database_service('patient_assigned', serializer.data)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        assignment = self.get_object()
        assignment.is_active = False
        assignment.save()
        
        # Notify database service
        self._notify_database_service('patient_unassigned', {'assignment_id': assignment.id})
        
        return Response({'message': 'Patient assignment deactivated'})
    
    def _notify_database_service(self, event_type, data):
        try:
            requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/events/",
                json={
                    'event_type': event_type,
                    'service': 'clinician-service',
                    'data': data
                }
            )
        except:
            pass

class ClinicianAppointmentViewSet(viewsets.ModelViewSet):
    queryset = ClinicianAppointment.objects.all()
    serializer_class = ClinicianAppointmentSerializer
    
    def get_queryset(self):
        # Filter appointments based on user role
        if hasattr(self.request, 'user_role'):
            if self.request.user_role == 'CLINICIAN':
                clinician = get_object_or_404(Clinician, user_id=self.request.user_id)
                return self.queryset.filter(clinician=clinician)
        return self.queryset
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        appointment = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(ClinicianAppointment.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.status = new_status
        appointment.save()
        
        # Notify database service
        self._notify_database_service('appointment_status_updated', {
            'appointment_id': appointment.id,
            'status': new_status
        })
        
        return Response({'message': f'Appointment status updated to {new_status}'})
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        # Get today's appointments
        clinician = get_object_or_404(Clinician, user_id=request.user_id)
        today = timezone.now().date()
        appointments = self.queryset.filter(
            clinician=clinician,
            appointment_date__date=today
        ).order_by('appointment_date')
        
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        # Get upcoming appointments
        clinician = get_object_or_404(Clinician, user_id=request.user_id)
        appointments = self.queryset.filter(
            clinician=clinician,
            appointment_date__gt=timezone.now(),
            status__in=['SCHEDULED', 'CONFIRMED']
        ).order_by('appointment_date')
        
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
    
    def _notify_database_service(self, event_type, data):
        try:
            requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/events/",
                json={
                    'event_type': event_type,
                    'service': 'clinician-service',
                    'data': data
                }
            )
        except:
            pass

class MedicalNoteViewSet(viewsets.ModelViewSet):
    queryset = MedicalNote.objects.all()
    serializer_class = MedicalNoteSerializer
    
    def get_queryset(self):
        # Filter medical notes based on user role
        if hasattr(self.request, 'user_role'):
            if self.request.user_role == 'CLINICIAN':
                clinician = get_object_or_404(Clinician, user_id=self.request.user_id)
                return self.queryset.filter(clinician=clinician)
        return self.queryset
    
    def create(self, request):
        # Clinicians create their own medical notes
        clinician = get_object_or_404(Clinician, user_id=request.user_id)
        data = request.data.copy()
        data['clinician'] = clinician.id
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            medical_note = serializer.save()
            
            # Create medical record in database service
            self._create_medical_record(medical_note)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _create_medical_record(self, medical_note):
        try:
            requests.post(
                f"{settings.DATABASE_SERVICE_URL}/api/medical-records/",
                json={
                    'patient_id': medical_note.patient_id,
                    'clinician_id': medical_note.clinician.user_id,
                    'clinician_name': f"Dr. {medical_note.clinician.first_name} {medical_note.clinician.last_name}",
                    'record_type': 'CONSULTATION',
                    'title': f"Consultation - {medical_note.chief_complaint[:50]}",
                    'description': medical_note.history_of_present_illness,
                    'diagnosis': medical_note.diagnosis,
                    'treatment': medical_note.treatment_plan,
                }
            )
        except:
            pass