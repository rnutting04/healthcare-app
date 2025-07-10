from rest_framework import serializers
from .models import User, Patient, Clinician, Appointment, MedicalRecord, Prescription, EventLog

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'phone_number', 
                 'date_of_birth', 'address', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class PatientSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
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
        return f"{obj.patient.user.first_name} {obj.patient.user.last_name}"
    
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
        return f"{obj.patient.user.first_name} {obj.patient.user.last_name}"
    
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
        return f"{obj.patient.user.first_name} {obj.patient.user.last_name}"
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.user.first_name} {obj.clinician.user.last_name}"

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