from rest_framework import serializers
from .models import User, Role, Patient, Clinician, Appointment, MedicalRecord, Prescription, EventLog, CancerType, FileMetadata, RAGDocument, Language

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
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'role_detail', 
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
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class ClinicianSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Clinician
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    clinician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_patient_name(self, obj):
        # Since Patient only has user_id, we can't get the name directly
        return f"Patient ID: {obj.patient.user_id}"
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.user.first_name} {obj.clinician.user.last_name}"

class MedicalRecordSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    clinician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_patient_name(self, obj):
        # Since Patient only has user_id, we can't get the name directly
        return f"Patient ID: {obj.patient.user_id}"
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.user.first_name} {obj.clinician.user.last_name}"

class PrescriptionSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    clinician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Prescription
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def get_patient_name(self, obj):
        # Since Patient only has user_id, we can't get the name directly
        return f"Patient ID: {obj.patient.user_id}"
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.user.first_name} {obj.clinician.user.last_name}"

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

class MedicalRecordCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    clinician_id = serializers.IntegerField()
    clinician_name = serializers.CharField()
    record_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    diagnosis = serializers.CharField(required=False, allow_blank=True)
    treatment = serializers.CharField(required=False, allow_blank=True)


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