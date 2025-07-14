from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Role, Patient, Clinician, Appointment, MedicalRecord, Prescription, EventLog, CancerType, UserEncryptionKey, FileMetadata, FileAccessLog, RAGDocument, RefreshToken, Language
from .serializers import (
    UserSerializer, PatientSerializer, ClinicianSerializer,
    AppointmentSerializer, MedicalRecordSerializer, PrescriptionSerializer,
    EventLogSerializer, MedicalRecordCreateSerializer, CancerTypeSerializer,
    FileMetadataSerializer, RAGDocumentSerializer, LanguageSerializer
)


class LanguageViewSet(viewsets.ModelViewSet):
    queryset = Language.objects.filter(is_active=True)
    serializer_class = LanguageSerializer
    
    def list(self, request):
        """List all active languages"""
        languages = self.get_queryset().order_by('display_order', 'name')
        data = [{
            'code': lang.code,
            'name': lang.name,
            'native_name': lang.native_name,
            'is_active': lang.is_active,
            'display_order': lang.display_order
        } for lang in languages]
        return Response(data)
    
    def retrieve(self, request, pk=None):
        """Get single language by code"""
        try:
            language = Language.objects.get(code=pk)
            return Response({
                'code': language.code,
                'name': language.name,
                'native_name': language.native_name,
                'is_active': language.is_active,
                'display_order': language.display_order
            })
        except Language.DoesNotExist:
            return Response({'error': 'Language not found'}, status=status.HTTP_404_NOT_FOUND)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = None  # We'll use custom responses
    
    def list(self, request):
        """List all roles"""
        roles = self.get_queryset()
        data = [{
            'id': role.id,
            'name': role.name,
            'display_name': role.display_name,
            'description': role.description,
            'created_at': role.created_at.isoformat() if role.created_at else None
        } for role in roles]
        return Response(data)
    
    def retrieve(self, request, pk=None):
        """Get single role"""
        try:
            role = self.get_object()
            return Response({
                'id': role.id,
                'name': role.name,
                'display_name': role.display_name,
                'description': role.description,
                'created_at': role.created_at.isoformat() if role.created_at else None
            })
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)


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
            user = User.objects.select_related('role').get(email=email)
            data = {
                'id': user.id,
                'email': user.email,
                'password': user.password,  # Include password for service-to-service auth
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': {
                    'id': user.role.id,
                    'name': user.role.name,
                    'display_name': user.role.display_name,
                    'description': user.role.description
                },
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'last_login': user.last_login
            }
            cache.set(cache_key, data, settings.CACHE_TTL)
            return Response(data)
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


class UserEncryptionKeyViewSet(viewsets.ModelViewSet):
    queryset = UserEncryptionKey.objects.all()
    serializer_class = None  # No serializer needed as we use custom actions
    
    @action(detail=False, methods=['get'])
    def get_or_create_key(self, request):
        """Get or create encryption key for a user"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
            key, created = UserEncryptionKey.objects.get_or_create(user=user)
            
            # Generate a new key if it doesn't exist
            if created or not key.key:
                from cryptography.fernet import Fernet
                key.key = Fernet.generate_key().decode()
                key.save()
            
            return Response({
                'user_id': user.id,
                'key': key.key,
                'created': created,
                'rotated_at': key.rotated_at
            })
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileMetadataViewSet(viewsets.ModelViewSet):
    queryset = FileMetadata.objects.all()
    serializer_class = FileMetadataSerializer
    
    @action(detail=False, methods=['post'])
    def check_duplicate(self, request):
        """Check if a file with the given hash already exists"""
        file_hash = request.data.get('file_hash')
        if not file_hash:
            return Response({'error': 'file_hash is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        exists = FileMetadata.objects.filter(file_hash=file_hash, is_deleted=False).exists()
        return Response({
            'exists': exists,
            'file_hash': file_hash
        })
    
    @action(detail=False, methods=['post'])
    def create_metadata(self, request):
        """Create file metadata record"""
        try:
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.get(id=user_id)
            
            # Check for duplicate
            file_hash = request.data.get('file_hash')
            if FileMetadata.objects.filter(file_hash=file_hash, is_deleted=False).exists():
                return Response({'error': 'File already exists'}, status=status.HTTP_409_CONFLICT)
            
            metadata = FileMetadata.objects.create(
                user=user,
                filename=request.data.get('filename'),
                file_hash=file_hash,
                file_size=request.data.get('file_size'),
                mime_type=request.data.get('mime_type'),
                storage_path=request.data.get('storage_path'),
                is_encrypted=request.data.get('is_encrypted', True)
            )
            
            # Log the upload
            FileAccessLog.objects.create(
                file=metadata,
                user=user,
                access_type='upload',
                ip_address=request.data.get('ip_address'),
                user_agent=request.data.get('user_agent'),
                success=True
            )
            
            return Response({
                'id': str(metadata.id),
                'filename': metadata.filename,
                'uploaded_at': metadata.uploaded_at
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def user_files(self, request):
        """Get all files for a specific user"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            files = FileMetadata.objects.filter(
                user_id=user_id,
                is_deleted=False
            ).order_by('-uploaded_at')
            
            files_data = [{
                'id': str(file.id),
                'filename': file.filename,
                'file_size': file.file_size,
                'mime_type': file.mime_type,
                'uploaded_at': file.uploaded_at,
                'last_accessed': file.last_accessed
            } for file in files]
            
            return Response(files_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def mark_deleted(self, request, pk=None):
        """Mark a file as deleted"""
        try:
            file = self.get_object()
            file.is_deleted = True
            file.deleted_at = timezone.now()
            file.save()
            
            # Log the deletion
            FileAccessLog.objects.create(
                file=file,
                user_id=request.data.get('user_id'),
                access_type='delete',
                ip_address=request.data.get('ip_address'),
                user_agent=request.data.get('user_agent'),
                success=True
            )
            
            return Response({'message': 'File marked as deleted'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def log_access(self, request, pk=None):
        """Log file access"""
        try:
            file = self.get_object()
            
            # Update last accessed time
            file.last_accessed = timezone.now()
            file.save()
            
            # Create access log
            FileAccessLog.objects.create(
                file=file,
                user_id=request.data.get('user_id'),
                access_type=request.data.get('access_type', 'download'),
                ip_address=request.data.get('ip_address'),
                user_agent=request.data.get('user_agent'),
                success=request.data.get('success', True),
                error_message=request.data.get('error_message')
            )
            
            return Response({'message': 'Access logged successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RAGDocumentViewSet(viewsets.ModelViewSet):
    queryset = RAGDocument.objects.select_related('file', 'cancer_type').all()
    serializer_class = RAGDocumentSerializer
    pagination_class = PageNumberPagination
    
    def list(self, request, *args, **kwargs):
        """List RAG documents with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply filtering if needed
        cancer_type_id = request.query_params.get('cancer_type_id')
        if cancer_type_id:
            queryset = queryset.filter(cancer_type_id=cancer_type_id)
        
        # Order by upload date
        queryset = queryset.order_by('-file__uploaded_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            # Use custom format for backwards compatibility
            data = []
            for rag_doc in page:
                data.append({
                    'file': str(rag_doc.file.id),
                    'cancer_type_id': rag_doc.cancer_type.id,
                    'cancer_type': rag_doc.cancer_type.cancer_type,
                    'file_data': {
                        'filename': rag_doc.file.filename,
                        'file_size': rag_doc.file.file_size,
                        'uploaded_at': rag_doc.file.uploaded_at.isoformat() if rag_doc.file.uploaded_at else None,
                        'mime_type': rag_doc.file.mime_type,
                    }
                })
            return self.get_paginated_response(data)
        
        # If pagination is not configured
        data = []
        for rag_doc in queryset:
            data.append({
                'file': str(rag_doc.file.id),
                'cancer_type_id': rag_doc.cancer_type.id,
                'cancer_type': rag_doc.cancer_type.cancer_type,
                'file_data': {
                    'filename': rag_doc.file.filename,
                    'file_size': rag_doc.file.file_size,
                    'uploaded_at': rag_doc.file.uploaded_at.isoformat() if rag_doc.file.uploaded_at else None,
                    'mime_type': rag_doc.file.mime_type,
                }
            })
        return Response(data)
    
    def create(self, request, *args, **kwargs):
        """Create RAG document association"""
        file_id = request.data.get('file_id')
        cancer_type_id = request.data.get('cancer_type_id')
        
        if not file_id or not cancer_type_id:
            return Response({'error': 'file_id and cancer_type_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Check if file exists
            file_metadata = FileMetadata.objects.get(id=file_id)
            
            # Check if cancer type exists
            cancer_type = CancerType.objects.get(id=cancer_type_id)
            
            # Create RAG document
            rag_doc = RAGDocument.objects.create(
                file=file_metadata,
                cancer_type=cancer_type
            )
            
            return Response({
                'file_id': str(rag_doc.file.id),
                'cancer_type_id': rag_doc.cancer_type.id,
                'cancer_type': rag_doc.cancer_type.cancer_type,
                'filename': rag_doc.file.filename
            }, status=status.HTTP_201_CREATED)
            
        except FileMetadata.DoesNotExist:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        except CancerType.DoesNotExist:
            return Response({'error': 'Cancer type not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def health_check(request):
    """Health check endpoint - requires authentication"""
    try:
        # Check database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check cache connection
        cache_status = 'connected'
        try:
            cache.set('health_check', 'ok', 10)
            cache.get('health_check')
        except:
            cache_status = 'disconnected'
        
        return Response({
            'status': 'healthy',
            'service': 'database-service',
            'database': 'connected',
            'cache': cache_status,
            'authenticated': True,
            'auth_type': getattr(request, 'auth', 'unknown')
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'service': 'database-service',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class RefreshTokenViewSet(viewsets.ModelViewSet):
    queryset = RefreshToken.objects.all()
    serializer_class = None  # We'll use custom actions
    
    @action(detail=False, methods=['post'])
    def create_token(self, request):
        """Create a new refresh token"""
        user_id = request.data.get('user_id')
        token = request.data.get('token')
        expires_at = request.data.get('expires_at')
        
        if not all([user_id, token, expires_at]):
            return Response({'error': 'user_id, token, and expires_at are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
            
            # Convert expires_at string to datetime
            from dateutil import parser
            expires_at_dt = parser.parse(expires_at)
            
            refresh_token = RefreshToken.objects.create(
                user=user,
                token=token,
                expires_at=expires_at_dt,
                is_active=True
            )
            
            return Response({
                'id': refresh_token.id,
                'user_id': user.id,
                'token': refresh_token.token,
                'created_at': refresh_token.created_at,
                'expires_at': refresh_token.expires_at,
                'is_active': refresh_token.is_active
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def validate_token(self, request):
        """Validate a refresh token"""
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'token parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh_token = RefreshToken.objects.select_related('user').get(
                token=token,
                is_active=True,
                expires_at__gt=timezone.now()
            )
            
            return Response({
                'id': refresh_token.id,
                'user_id': refresh_token.user.id,
                'user_email': refresh_token.user.email,
                'expires_at': refresh_token.expires_at,
                'is_valid': True
            })
        except RefreshToken.DoesNotExist:
            return Response({'is_valid': False}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def invalidate_token(self, request):
        """Invalidate a refresh token"""
        token = request.data.get('token')
        if not token:
            return Response({'error': 'token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh_token = RefreshToken.objects.get(token=token)
            refresh_token.is_active = False
            refresh_token.save()
            
            return Response({'message': 'Token invalidated successfully'})
        except RefreshToken.DoesNotExist:
            return Response({'error': 'Token not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def invalidate_user_tokens(self, request):
        """Invalidate all refresh tokens for a user"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        count = RefreshToken.objects.filter(user_id=user_id, is_active=True).update(is_active=False)
        
        return Response({
            'message': f'Invalidated {count} tokens for user',
            'count': count
        })
    
    @action(detail=False, methods=['delete'])
    def cleanup_expired(self, request):
        """Delete expired refresh tokens"""
        count, _ = RefreshToken.objects.filter(expires_at__lt=timezone.now()).delete()
        
        return Response({
            'message': f'Deleted {count} expired tokens',
            'count': count
        })