from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Patient, Clinician, Appointment, MedicalRecord, Prescription, EventLog, CancerType
from .serializers import (
    UserSerializer, PatientSerializer, ClinicianSerializer,
    AppointmentSerializer, MedicalRecordSerializer, PrescriptionSerializer,
    EventLogSerializer, MedicalRecordCreateSerializer, CancerTypeSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        role = self.request.query_params.get('role')
        is_active = self.request.query_params.get('is_active')
        
        if role:
            queryset = queryset.filter(role__name=role)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset.select_related('role')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get user statistics for admin dashboard"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Get counts by role
        total_users = User.objects.count()
        active_patients = User.objects.filter(role__name='PATIENT', is_active=True).count()
        active_clinicians = User.objects.filter(role__name='CLINICIAN', is_active=True).count()
        total_admins = User.objects.filter(role__name='ADMIN').count()
        inactive_users = User.objects.filter(is_active=False).count()
        
        # Get new users in last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        new_users_week = User.objects.filter(date_joined__gte=week_ago).count()
        
        return Response({
            'total_users': total_users,
            'active_patients': active_patients,
            'active_clinicians': active_clinicians,
            'total_admins': total_admins,
            'inactive_users': inactive_users,
            'new_users_week': new_users_week
        })
    
    @action(detail=False, methods=['get'])
    def by_email(self, request):
        email = request.query_params.get('email')
        if not email:
            return Response({'error': 'Email parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check cache first
        cache_key = f"user_email_{email}"
        cached_user = cache.get(cache_key)
        if cached_user:
            return Response(cached_user)
        
        try:
            user = User.objects.get(email=email)
            serializer = self.get_serializer(user)
            cache.set(cache_key, serializer.data, settings.CACHE_TTL)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    
    @action(detail=False, methods=['get'])
    def by_user(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(user_id=user_id)
            serializer = self.get_serializer(patient)
            return Response(serializer.data)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

class ClinicianViewSet(viewsets.ModelViewSet):
    queryset = Clinician.objects.select_related('user').all()
    serializer_class = ClinicianSerializer
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        clinicians = self.queryset.filter(is_available=True)
        serializer = self.get_serializer(clinicians, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_specialization(self, request):
        specialization = request.query_params.get('specialization')
        if not specialization:
            return Response({'error': 'specialization parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        clinicians = self.queryset.filter(specialization__icontains=specialization)
        serializer = self.get_serializer(clinicians, many=True)
        return Response(serializer.data)

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('patient', 'clinician__user').all()
    serializer_class = AppointmentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by patient
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        # Filter by clinician
        clinician_id = self.request.query_params.get('clinician_id')
        if clinician_id:
            queryset = queryset.filter(clinician_id=clinician_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                appointment_date__gte=start_date,
                appointment_date__lte=end_date
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('appointment_date')
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        # Cache key based on query params
        patient_id = request.query_params.get('patient_id')
        clinician_id = request.query_params.get('clinician_id')
        cache_key = f"upcoming_appointments_{patient_id}_{clinician_id}"
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        queryset = self.queryset.filter(
            appointment_date__gte=timezone.now(),
            status__in=['SCHEDULED', 'CONFIRMED']
        )
        
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if clinician_id:
            queryset = queryset.filter(clinician_id=clinician_id)
        
        appointments = queryset.order_by('appointment_date')[:20]
        serializer = self.get_serializer(appointments, many=True)
        
        cache.set(cache_key, serializer.data, 300)  # Cache for 5 minutes
        return Response(serializer.data)

class MedicalRecordViewSet(viewsets.ModelViewSet):
    queryset = MedicalRecord.objects.select_related('patient', 'clinician__user', 'appointment').all()
    serializer_class = MedicalRecordSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by patient
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        # Filter by record type
        record_type = self.request.query_params.get('record_type')
        if record_type:
            queryset = queryset.filter(record_type=record_type)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def create_from_service(self, request):
        serializer = MedicalRecordCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            try:
                patient = Patient.objects.get(user_id=data['patient_id'])
                clinician = Clinician.objects.get(user_id=data['clinician_id'])
                
                medical_record = MedicalRecord.objects.create(
                    patient=patient,
                    clinician=clinician,
                    record_type=data['record_type'],
                    title=data['title'],
                    description=data['description'],
                    diagnosis=data.get('diagnosis', ''),
                    treatment=data.get('treatment', '')
                )
                
                response_serializer = MedicalRecordSerializer(medical_record)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except (Patient.DoesNotExist, Clinician.DoesNotExist) as e:
                return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.select_related('patient', 'clinician__user', 'medical_record').all()
    serializer_class = PrescriptionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by patient
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def active_by_patient(self, request):
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        prescriptions = self.queryset.filter(
            patient_id=patient_id,
            is_active=True,
            end_date__gte=timezone.now().date()
        )
        
        serializer = self.get_serializer(prescriptions, many=True)
        return Response(serializer.data)

@api_view(['POST'])
def log_event(request):
    serializer = EventLogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def statistics(request):
    # Cache statistics for better performance
    cache_key = "database_statistics"
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return Response(cached_stats)
    
    stats = {
        'total_users': User.objects.count(),
        'total_patients': Patient.objects.count(),
        'total_clinicians': Clinician.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'upcoming_appointments': Appointment.objects.filter(
            appointment_date__gte=timezone.now(),
            status__in=['SCHEDULED', 'CONFIRMED']
        ).count(),
        'total_medical_records': MedicalRecord.objects.count(),
        'active_prescriptions': Prescription.objects.filter(
            is_active=True,
            end_date__gte=timezone.now().date()
        ).count(),
    }
    
    cache.set(cache_key, stats, 3600)  # Cache for 1 hour
    return Response(stats)

class CancerTypeViewSet(viewsets.ModelViewSet):
    queryset = CancerType.objects.all()
    serializer_class = CancerTypeSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by parent (to get only top-level types or subtypes)
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            if parent_id == 'null':
                # Get only top-level cancer types
                queryset = queryset.filter(parent__isnull=True)
            else:
                # Get subtypes of a specific parent
                queryset = queryset.filter(parent_id=parent_id)
        
        # Search by cancer type name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(cancer_type__icontains=search)
        
        return queryset.order_by('cancer_type')
    
    @action(detail=False, methods=['get'])
    def top_level(self, request):
        """Get only top-level cancer types (no parent)"""
        cancer_types = self.queryset.filter(parent__isnull=True).order_by('cancer_type')
        serializer = self.get_serializer(cancer_types, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def subtypes(self, request, pk=None):
        """Get all subtypes of a specific cancer type"""
        cancer_type = self.get_object()
        subtypes = cancer_type.subtypes.all().order_by('cancer_type')
        serializer = self.get_serializer(subtypes, many=True)
        return Response(serializer.data)