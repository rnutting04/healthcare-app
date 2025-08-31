from rest_framework import serializers
from .models import User, Role, Patient, Clinician, EventLog, CancerType, FileMetadata, RAGDocument, Language, RAGEmbedding, RAGEmbeddingJob, PatientAssignment, MedicalRecordType, MedicalRecord, MedicalRecordAccess, ChatMessage, ChatSession

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = '__all__'

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'display_name', 'description']

class UserSerializer(serializers.ModelSerializer):
    role_detail = RoleSerializer(source='role', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'role', 'role_detail', 
                 'role_name', 'is_active', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'role_detail', 'role_name']

class PatientSerializer(serializers.ModelSerializer):
    preferred_language_id = serializers.PrimaryKeyRelatedField(
        source='preferred_language',
        queryset=Language.objects.all(),
        required=False,
        allow_null=True
    )
    preferred_language = serializers.CharField(source='preferred_language.code', read_only=True)
    phone_number = serializers.CharField(allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)
    emergency_contact_name = serializers.CharField(allow_blank=True, required=False)
    emergency_contact_phone = serializers.CharField(allow_blank=True, required=False)
    user = UserSerializer(read_only=True)
    assignment = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_assignment(self, obj):
        """Get patient assignment details if available"""
        try:
            if hasattr(obj, 'assignment'):
                assignment = obj.assignment
                return {
                    'id': assignment.id,
                    'cancer_subtype': assignment.cancer_subtype.id if assignment.cancer_subtype else None,
                    'cancer_subtype_name': assignment.cancer_subtype.cancer_type if assignment.cancer_subtype else None,
                    'assigned_clinician': assignment.assigned_clinician.id if assignment.assigned_clinician else None,
                    'notes': assignment.notes,
                    'created_at': assignment.created_at.isoformat() if assignment.created_at else None,
                    'updated_at': assignment.updated_at.isoformat() if assignment.updated_at else None
                }
        except:
            pass
        return None

class ClinicianSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    specialization_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Clinician
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_specialization_detail(self, obj):
        if obj.specialization:
            return {
                'id': obj.specialization.id,
                'cancer_type': obj.specialization.cancer_type,
                'description': obj.specialization.description
            }
        return None

class CancerTypeSerializer(serializers.ModelSerializer):
    subtypes = serializers.SerializerMethodField()
    parent_details = serializers.SerializerMethodField()
    
    class Meta:
        model = CancerType
        fields = ['id', 'cancer_type', 'description', 'parent', 'parent_details', 'subtypes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_subtypes(self, obj):
        # Get all subtypes of this cancer type
        subtypes = obj.subtypes.all()
        return CancerTypeSerializer(subtypes, many=True, read_only=True).data
    
    def get_parent_details(self, obj):
        if obj.parent:
            return {
                'id': obj.parent.id,
                'cancer_type': obj.parent.cancer_type
            }
        return None

class EventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventLog
        fields = '__all__'
        read_only_fields = ['created_at']

class FileMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileMetadata
        fields = '__all__'
        read_only_fields = ['id', 'uploaded_at', 'last_accessed', 'deleted_at']


class RAGDocumentSerializer(serializers.ModelSerializer):
    cancer_type_name = serializers.CharField(source='cancer_type.cancer_type', read_only=True)
    file_data = FileMetadataSerializer(source='file', read_only=True)
    
    class Meta:
        model = RAGDocument
        fields = ['file', 'cancer_type', 'cancer_type_name', 'file_data']


# RAG Embedding serializers
class RAGEmbeddingSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source='document.file.filename', read_only=True)
    
    class Meta:
        model = RAGEmbedding
        fields = ['id', 'document', 'document_name', 'chunk_index', 'chunk_text', 
                 'embedding', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']


class RAGEmbeddingJobSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source='document.file.filename', read_only=True)
    
    class Meta:
        model = RAGEmbeddingJob
        fields = ['id', 'document', 'document_name', 'status', 'message', 
                 'created_at', 'updated_at', 'completed_at', 'retry_count']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmbeddingCreateSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    cancer_type_id = serializers.IntegerField()
    chunk_index = serializers.IntegerField()
    chunk_text = serializers.CharField()
    embedding = serializers.ListField(
        child=serializers.FloatField(),
        min_length=1536,
        max_length=1536
    )
    metadata = serializers.JSONField(required=False, default=dict)


class BulkEmbeddingCreateSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    chunks = serializers.ListField(
        child=EmbeddingCreateSerializer(),
        allow_empty=False
    )


class EmbeddingSearchSerializer(serializers.Serializer):
    query_embedding = serializers.ListField(
        child=serializers.FloatField(),
        min_length=1536,
        max_length=1536
    )
    cancer_type_id = serializers.IntegerField(required=False, allow_null=True)
    k = serializers.IntegerField(default=5, min_value=1, max_value=50)


class PatientAssignmentSerializer(serializers.ModelSerializer):
    cancer_subtype_detail = serializers.SerializerMethodField()
    assigned_clinician_detail = serializers.SerializerMethodField()
    updated_by_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientAssignment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_cancer_subtype_detail(self, obj):
        if obj.cancer_subtype:
            return {
                'id': obj.cancer_subtype.id,
                'cancer_type': obj.cancer_subtype.cancer_type,
                'parent': obj.cancer_subtype.parent.cancer_type if obj.cancer_subtype.parent else None
            }
        return None
    
    def get_assigned_clinician_detail(self, obj):
        if obj.assigned_clinician:
            return {
                'id': obj.assigned_clinician.id,
                'name': f"Dr. {obj.assigned_clinician.user.first_name} {obj.assigned_clinician.user.last_name}",
                'specialization': obj.assigned_clinician.specialization.cancer_type if obj.assigned_clinician.specialization else None
            }
        return None
    
    def get_updated_by_detail(self, obj):
        if obj.updated_by:
            return {
                'id': obj.updated_by.id,
                'name': f"{obj.updated_by.first_name} {obj.updated_by.last_name}",
                'email': obj.updated_by.email
            }
        return None


class MedicalRecordTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecordType
        fields = ['id', 'type_name', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class MedicalRecordSerializer(serializers.ModelSerializer):
    file_detail = FileMetadataSerializer(source='file', read_only=True)
    patient_detail = serializers.SerializerMethodField()
    medical_record_type_detail = MedicalRecordTypeSerializer(source='medical_record_type', read_only=True)
    uploaded_by_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalRecord
        fields = ['file', 'patient', 'medical_record_type', 'uploaded_by', 'created_at', 
                  'file_detail', 'patient_detail', 'medical_record_type_detail', 'uploaded_by_detail']
        read_only_fields = ['created_at', 'file_detail', 'patient_detail', 'medical_record_type_detail', 'uploaded_by_detail']
    
    def get_patient_detail(self, obj):
        """Get basic patient info"""
        return {
            'id': obj.patient.id,
            'name': f"{obj.patient.user.first_name} {obj.patient.user.last_name}" if hasattr(obj.patient, 'user') else 'Unknown'
        }
    
    def get_uploaded_by_detail(self, obj):
        """Get uploader info"""
        if obj.uploaded_by:
            return {
                'id': obj.uploaded_by.id,
                'name': f"{obj.uploaded_by.first_name} {obj.uploaded_by.last_name}",
                'email': obj.uploaded_by.email
            }
        return None


class MedicalRecordAccessSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    granted_by_detail = UserSerializer(source='granted_by', read_only=True)
    
    class Meta:
        model = MedicalRecordAccess
        fields = ['id', 'medical_record', 'user', 'encrypted_access_key', 'granted_by', 'granted_at', 
                  'expires_at', 'revoked_at', 'is_active', 'user_detail', 'granted_by_detail']
        read_only_fields = ['granted_at', 'is_active', 'user_detail', 'granted_by_detail']

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ChatMessage
        fields = ["id", "session_id", "role", "content", "timestamp"]

class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model  = ChatSession
        fields = ["id","patient_id", "title", "created_at", "messages", "suggestions"]
