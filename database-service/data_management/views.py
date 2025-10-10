from rest_framework import viewsets, status, filters, permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Role, Patient, Clinician, EventLog, CancerType, UserEncryptionKey, FileMetadata, FileAccessLog, RAGDocument, RefreshToken, Language, RAGEmbedding, RAGEmbeddingJob, PatientAssignment, MedicalRecordType, MedicalRecord, MedicalRecordAccess, ChatMessage, ChatSession
from .models import SuggestionTemplate, SuggestedHistory
from .serializers import (
    UserSerializer, PatientSerializer, ClinicianSerializer,
    EventLogSerializer, CancerTypeSerializer,
    FileMetadataSerializer, RAGDocumentSerializer, LanguageSerializer,
    RAGEmbeddingSerializer, RAGEmbeddingJobSerializer, EmbeddingCreateSerializer,
    BulkEmbeddingCreateSerializer, EmbeddingSearchSerializer, PatientAssignmentSerializer,
    MedicalRecordTypeSerializer, MedicalRecordSerializer, MedicalRecordAccessSerializer,
    ChatMessageSerializer, ChatSessionSerializer, SuggestionTemplateSerializer, SuggestedHistorySerializer
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
    
    @action(detail=False, methods=['get'])
    def by_clinician(self, request):
        """Get all patients assigned to a specific clinician"""
        clinician_id = request.query_params.get('clinician_id')
        if not clinician_id:
            return Response({'error': 'clinician_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get patients through PatientAssignment
            patients = Patient.objects.filter(
                assignment__assigned_clinician_id=clinician_id
            ).select_related('preferred_language', 'assignment', 'assignment__cancer_subtype')
            
            # Get user data for each patient
            patient_data = []
            for patient in patients:
                patient_dict = self.get_serializer(patient).data
                # Fetch user data separately
                try:
                    user = User.objects.get(id=patient.user_id)
                    patient_dict['user'] = UserSerializer(user).data
                except User.DoesNotExist:
                    patient_dict['user'] = None
                patient_data.append(patient_dict)
            
            return Response(patient_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ClinicianViewSet(viewsets.ModelViewSet):
    queryset = Clinician.objects.select_related('user', 'specialization').all()
    serializer_class = ClinicianSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new clinician profile"""
        user_id = request.data.get('user_id')
        specialization_id = request.data.get('specialization_id')
        phone_number = request.data.get('phone_number', '')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get user
            user = User.objects.get(id=user_id)
            
            # Get specialization if provided
            specialization = None
            if specialization_id:
                specialization = CancerType.objects.get(id=specialization_id, parent__isnull=True)
            
            # Create clinician
            clinician = Clinician.objects.create(
                user=user,
                specialization=specialization,
                phone_number=phone_number,
                is_available=True
            )
            
            serializer = self.get_serializer(clinician)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except CancerType.DoesNotExist:
            return Response({'error': 'Invalid specialization'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_user(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            clinician = Clinician.objects.select_related('user', 'specialization').get(user__id=user_id)
            serializer = self.get_serializer(clinician)
            return Response(serializer.data)
        except Clinician.DoesNotExist:
            return Response({'error': 'Clinician not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        clinicians = self.queryset.filter(is_available=True)
        serializer = self.get_serializer(clinicians, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_specialization(self, request):
        specialization_id = request.query_params.get('specialization_id')
        if not specialization_id:
            return Response({'error': 'specialization_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        clinicians = self.queryset.filter(specialization__id=specialization_id)
        serializer = self.get_serializer(clinicians, many=True)
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
        'total_clinicians': User.objects.filter(role__name='CLINICIAN').count(),
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


# RAG Embedding Views
class RAGEmbeddingViewSet(viewsets.ModelViewSet):
    queryset = RAGEmbedding.objects.all()
    serializer_class = RAGEmbeddingSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by document
        document_id = self.request.query_params.get('document')
        if document_id:
            queryset = queryset.filter(document__file=document_id)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def create_embedding(self, request):
        """Create a single embedding"""
        serializer = EmbeddingCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Get document
                document = RAGDocument.objects.get(file_id=serializer.validated_data['document_id'])
                
                # Create embedding
                embedding = RAGEmbedding.objects.create(
                    document=document,
                    chunk_index=serializer.validated_data['chunk_index'],
                    chunk_text=serializer.validated_data['chunk_text'],
                    embedding=serializer.validated_data['embedding'],
                    metadata=serializer.validated_data.get('metadata', {})
                )
                
                # Also store in vector column
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE rag_embeddings SET embedding_vector = %s WHERE id = %s",
                        [serializer.validated_data['embedding'], str(embedding.id)]
                    )
                
                return Response(
                    RAGEmbeddingSerializer(embedding).data,
                    status=status.HTTP_201_CREATED
                )
            except RAGDocument.DoesNotExist:
                return Response(
                    {'error': 'Document not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple embeddings at once"""
        serializer = BulkEmbeddingCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                document_id = serializer.validated_data['document_id']
                document = RAGDocument.objects.get(file_id=document_id)
                
                created_embeddings = []
                for chunk_data in serializer.validated_data['chunks']:
                    embedding = RAGEmbedding.objects.create(
                        document=document,
                        chunk_index=chunk_data['chunk_index'],
                        chunk_text=chunk_data['chunk_text'],
                        embedding=chunk_data['embedding'],
                        metadata=chunk_data.get('metadata', {})
                    )
                    created_embeddings.append(embedding)
                
                # Bulk update vector column
                from django.db import connection
                with connection.cursor() as cursor:
                    for i, embedding in enumerate(created_embeddings):
                        cursor.execute(
                            "UPDATE rag_embeddings SET embedding_vector = %s WHERE id = %s",
                            [serializer.validated_data['chunks'][i]['embedding'], str(embedding.id)]
                        )
                
                return Response({
                    'message': f'Created {len(created_embeddings)} embeddings',
                    'count': len(created_embeddings)
                }, status=status.HTTP_201_CREATED)
                
            except RAGDocument.DoesNotExist:
                return Response(
                    {'error': 'Document not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """Search for similar embeddings using vector similarity"""
        serializer = EmbeddingSearchSerializer(data=request.data)
        if serializer.is_valid():
            try:
                query_embedding = serializer.validated_data['query_embedding']
                cancer_type_id = serializer.validated_data.get('cancer_type_id')
                k = serializer.validated_data['k']
                
                # Build query with PGVector
                from django.db import connection
                
                if cancer_type_id:
                    query = """
                        SELECT e.id, e.chunk_text, e.metadata, 
                               e.embedding_vector <=> %s::vector as distance,
                               d.file_id, f.filename
                        FROM rag_embeddings e
                        JOIN rag_documents d ON e.document_id = d.file_id
                        JOIN file_metadata f ON d.file_id = f.id
                        WHERE d.cancer_type_id = %s
                        ORDER BY e.embedding_vector <=> %s::vector
                        LIMIT %s
                    """
                    params = [query_embedding, cancer_type_id, query_embedding, k]
                else:
                    query = """
                        SELECT e.id, e.chunk_text, e.metadata, 
                               e.embedding_vector <=> %s::vector as distance,
                               d.file_id, f.filename
                        FROM rag_embeddings e
                        JOIN rag_documents d ON e.document_id = d.file_id
                        JOIN file_metadata f ON d.file_id = f.id
                        ORDER BY e.embedding_vector <=> %s::vector
                        LIMIT %s
                    """
                    params = [query_embedding, query_embedding, k]
                
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                    results = []
                    for row in cursor.fetchall():
                        results.append({
                            'id': str(row[0]),
                            'chunk_text': row[1],
                            'metadata': row[2],
                            'distance': float(row[3]),
                            'document_id': str(row[4]),
                            'document_name': row[5]
                        })
                
                return Response({
                    'results': results,
                    'count': len(results)
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def has_embeddings(self, request):
        """Check if a document has embeddings"""
        document_id = request.query_params.get('document_id')
        if not document_id:
            return Response(
                {'error': 'document_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        exists = RAGEmbedding.objects.filter(document__file=document_id).exists()
        return Response({'has_embeddings': exists})


class RAGEmbeddingJobViewSet(viewsets.ModelViewSet):
    queryset = RAGEmbeddingJob.objects.all()
    serializer_class = RAGEmbeddingJobSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'status', 'id']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['post'])
    def create_status(self, request):
        """Create initial job status"""
        job_id = request.data.get('job_id')
        document_id = request.data.get('document_id')
        status_value = request.data.get('status', 'pending')
        message = request.data.get('message', '')
        
        if not all([job_id, document_id]):
            return Response(
                {'error': 'job_id and document_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            document = RAGDocument.objects.get(file_id=document_id)
            job = RAGEmbeddingJob.objects.create(
                id=job_id,
                document=document,
                status=status_value,
                message=message
            )
            
            return Response(
                RAGEmbeddingJobSerializer(job).data,
                status=status.HTTP_201_CREATED
            )
        except RAGDocument.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['put'])
    def update_status(self, request, pk=None):
        """Update job status"""
        try:
            job = RAGEmbeddingJob.objects.get(id=pk)
            job.status = request.data.get('status', job.status)
            job.message = request.data.get('message', job.message)
            
            if job.status == 'completed':
                job.completed_at = timezone.now()
            
            job.save()
            
            return Response(RAGEmbeddingJobSerializer(job).data)
            
        except RAGEmbeddingJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get embedding job statistics"""
        from django.db.models import Count
        
        stats = RAGEmbeddingJob.objects.values('status').annotate(count=Count('status'))
        
        total_processed = RAGEmbedding.objects.values('document').distinct().count()
        
        return Response({
            'job_stats': list(stats),
            'total_documents_processed': total_processed,
            'total_embeddings': RAGEmbedding.objects.count()
        })


# Old embedding code - to be removed
@api_view(['GET'])
def check_document_embeddings(request, document_id):
    """Check if document has embeddings"""
    has_embeddings = RAGEmbedding.objects.filter(document_id=document_id).exists()
    return Response({'has_embeddings': has_embeddings})


class PatientAssignmentViewSet(viewsets.ModelViewSet):
    queryset = PatientAssignment.objects.select_related('patient', 'cancer_subtype', 'assigned_clinician', 'updated_by').all()
    serializer_class = PatientAssignmentSerializer
    
    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """Get assignment by patient ID"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            assignment = PatientAssignment.objects.select_related(
                'patient', 'cancer_subtype', 'assigned_clinician', 'updated_by'
            ).get(patient_id=patient_id)
            serializer = self.get_serializer(assignment)
            return Response(serializer.data)
        except PatientAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def create(self, request, *args, **kwargs):
        """Create or update patient assignment"""
        patient_id = request.data.get('patient')
        if not patient_id:
            return Response({'error': 'patient is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if assignment already exists
        try:
            assignment = PatientAssignment.objects.get(patient_id=patient_id)
            # Update existing assignment
            serializer = self.get_serializer(assignment, data=request.data, partial=True)
        except PatientAssignment.DoesNotExist:
            # Create new assignment
            serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """Update patient assignment"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Set updated_by to the requesting user (if available)
        if 'updated_by' not in request.data and hasattr(request, 'user'):
            request.data['updated_by'] = request.user.id
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def check_assignment(self, request):
        """Check if a clinician is assigned to a patient"""
        patient_id = request.query_params.get('patient_id')
        clinician_user_id = request.query_params.get('clinician_user_id')
        
        if not patient_id or not clinician_user_id:
            return Response({'error': 'patient_id and clinician_user_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get clinician by user ID
            clinician = Clinician.objects.get(user_id=clinician_user_id)
            
            # Check if patient is assigned to this clinician
            assignment_exists = PatientAssignment.objects.filter(
                patient_id=patient_id,
                assigned_clinician=clinician
            ).exists()
            
            return Response({
                'is_assigned': assignment_exists,
                'patient_id': patient_id,
                'clinician_id': clinician.id,
                'clinician_user_id': clinician_user_id
            })
        except Clinician.DoesNotExist:
            return Response({
                'is_assigned': False,
                'error': 'Clinician not found'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicalRecordTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for medical record types (read-only since these are predefined)
    """
    queryset = MedicalRecordType.objects.filter(is_active=True).order_by('type_name')
    serializer_class = MedicalRecordTypeSerializer
    
    def list(self, request):
        """List all active medical record types"""
        types = self.get_queryset()
        serializer = self.get_serializer(types, many=True)
        return Response(serializer.data)


class MedicalRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for medical records
    """
    queryset = MedicalRecord.objects.all()
    serializer_class = MedicalRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['patient', 'medical_record_type']
    ordering_fields = ['file__uploaded_at']
    ordering = ['-file__uploaded_at']
    
    def get_queryset(self):
        """Filter medical records by patient if specified"""
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset.select_related('file', 'patient', 'medical_record_type')
    
    def create(self, request):
        """Create a new medical record"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """Get all medical records for a specific patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        records = self.get_queryset().filter(patient_id=patient_id)
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)


class MedicalRecordAccessViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing medical record access permissions
    """
    queryset = MedicalRecordAccess.objects.all()
    serializer_class = MedicalRecordAccessSerializer
    
    def get_queryset(self):
        """Filter access records"""
        queryset = super().get_queryset()
        
        # Filter by medical record
        medical_record_id = self.request.query_params.get('medical_record_id')
        if medical_record_id:
            queryset = queryset.filter(medical_record_id=medical_record_id)
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter only active access
        if self.request.query_params.get('active_only', 'true').lower() == 'true':
            queryset = queryset.filter(revoked_at__isnull=True)
            # Also check expiry
            now = timezone.now()
            queryset = queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=now)
            )
        
        return queryset.select_related('medical_record', 'user', 'granted_by')
    
    def create(self, request):
        """Grant access to a medical record"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke access to a medical record"""
        access = self.get_object()
        access.revoked_at = timezone.now()
        access.save()
        
        return Response({
            'message': 'Access revoked successfully',
            'revoked_at': access.revoked_at
        })
    
        
class ChatViewSet(viewsets.ViewSet):

    def _session_for_user_or_403(self, request, sid: str) -> ChatSession:
        if not sid:
            raise NotFound("session_id required")

        session = (
            ChatSession.objects
            .select_related("patient")
            .filter(id=sid, patient__user_id=request.user.id)   # <- change if your field names differ
            .first()
        )
        if not session:
            # Either it doesn't exist OR it's not owned by this user
            raise PermissionDenied("You do not have access to this session")
        return session

    @action(detail=False, methods=['get'])
    def sessions(self, request):
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        sessions = ChatSession.objects.filter(patient_id=patient_id).order_by('-created_at')
        return Response(ChatSessionSerializer(sessions, many=True).data)

    @action(detail=False, methods=['post'])
    def start(self, request):
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        session = ChatSession.objects.create(patient_id=patient_id, title="New Chat")
        return Response(ChatSessionSerializer(session).data)

    @action(detail=False, methods=['get'])
    def load(self, request):
        session_id = request.query_params.get('session_id')
        patient_id = request.query_params.get('patient_id')
        if not session_id or not patient_id:
            return Response({'error': 'session_id and patient_id are required'}, status=400)
        session = ChatSession.objects.filter(id=session_id, patient_id=patient_id).first()
        if not session:
            return Response({'error': 'Session not found'}, status=404)
        return Response(ChatSessionSerializer(session).data)

    @action(detail=False, methods=['get'])
    def messages(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': 'session_id is required'}, status=400)
        messages = ChatMessage.objects.filter(session_id=session_id).order_by('timestamp')
        return Response(ChatMessageSerializer(messages, many=True).data)

    @action(detail=False, methods=['post'])
    def message(self, request):
        session_id = request.data.get('session_id')
        role = request.data.get('role')
        content = request.data.get('content')

        if not session_id or not role or not content:
            return Response({'error': 'session_id, role, and content are required'}, status=400)

        msg = ChatMessage.objects.create(session_id=session_id, role=role, content=content)
        return Response(ChatMessageSerializer(msg).data)

    @action(detail=False, methods=['post'])
    def rename_session(self, request):
        session_id = request.data.get('session_id')
        title = request.data.get('title')

        if not session_id or not title:
            return Response({'error': 'session_id and title required'}, status=400)

        session = ChatSession.objects.filter(id=session_id).first()
        session.title = title
        session.save(update_fields=['title'])
        return Response({'success': True})

    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        patient_id = request.query_params.get('patient_id')
        session = ChatSession.objects.filter(id=pk, patient_id=patient_id).first()
        if session:
            session.delete()
            return Response({'message': 'Session deleted.'})
        return Response({'error': 'Session not found or delete failed.'}, status=400)

    @action(detail=False, methods=['post'])
    def suggestions(self, request):
        session_id = request.data.get('session_id')
        suggestions = request.data.get('suggestions')
        if not session_id or not suggestions:
            return Response({'error': 'Session ID or suggestions not provided.'}, status=400)
        
        session = ChatSession.objects.filter(id=session_id).first()
        if not session:
            return Response({'error': 'Session not found.'}, status=404)
        
        session.suggestions = suggestions
        session.save(update_fields=['suggestions'])
        return Response({'success': True})
    @action(detail=False, methods=['get'], url_path='internal/sessions/last-messages')

    def internal_last_messages(self, request):
        sid = request.query_params.get('session_id')
        limit = int(request.query_params.get('limit', 5))
        session = self._session_for_user_or_403(request, sid)
        msgs = ChatMessage.objects.filter(session=session).order_by('-timestamp')[:limit]
        msgs = list(reversed(list(msgs)))  # chronological
        return Response(ChatMessageSerializer(msgs, many=True).data, status=200)

    @action(detail=False, methods=['get'], url_path='internal/suggestions/templates')
    def internal_templates(self, request):
        # templates are global; no ownership check
        ct = (request.query_params.get('cancer_type') or '').strip().lower()
        qs = SuggestionTemplate.objects.filter(cancer_type=ct) if ct else SuggestionTemplate.objects.all()
        return Response(SuggestionTemplateSerializer(qs, many=True).data, status=200)

    @action(detail=False, methods=['get', 'post'], url_path='internal/suggestions/history',
            permission_classes=[permissions.IsAuthenticated])
    def internal_suggestions_history(self, request):
        if request.method == 'GET':
            sid = request.query_params.get('session_id')
            session = self._session_for_user_or_403(request, sid)
            texts = list(SuggestedHistory.objects.filter(session=session)
                        .values_list('text', flat=True))
            return Response(texts, status=200)

        # POST: append used items to history
        sid   = request.data.get('session_id')
        items = request.data.get('items') or []
        session = self._session_for_user_or_403(request, sid)
        objs = [SuggestedHistory(session=session, text=t) for t in items[:4]]
        SuggestedHistory.objects.bulk_create(objs, ignore_conflicts=True)  # unique_together(session,text)
        return Response({'success': True}, status=200)

    # Store last 4 on the session so the UI can reload them
    @action(detail=False, methods=['post'], url_path='suggestions')
    def store_last4(self, request):
        sid   = request.data.get('session_id')
        items = request.data.get('suggestions') or []
        session = self._session_for_user_or_403(request, sid)
        session.suggestions = items[:4]
        session.save(update_fields=['suggestions'])
        return Response({'success': True}, status=200)

    @action(detail=False, methods=['post'], url_path='internal/suggestions/upsert-embeddings',
            permission_classes=[permissions.IsAuthenticated])
    def internal_upsert_embeddings(self, request):
        items = request.data.get('items') or []  # [{id, embedding}]
        if not isinstance(items, list):
            return Response({'error':'items must be a list'}, status=400)

        # (No session ownership required here; it’s template data.)
        updated = 0
        for it in items:
            sid = it.get('id'); emb = it.get('embedding')
            if sid is None or emb is None: 
                continue
            SuggestionTemplate.objects.filter(id=sid).update(embedding_json=emb)
            updated += 1
        return Response({'updated': updated}, status=200)
