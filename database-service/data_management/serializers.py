from rest_framework import serializers
from .models import User, Role, Patient, EventLog, CancerType, FileMetadata, RAGDocument, Language, RAGEmbedding, RAGEmbeddingJob

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
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

# class ClinicianSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)
#     
#     class Meta:
#         model = Clinician
#         fields = '__all__'
#         read_only_fields = ['created_at', 'updated_at']

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