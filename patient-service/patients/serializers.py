from rest_framework import serializers
from django.utils import timezone
from .models import Patient, Appointment, MedicalRecord, Prescription, Language

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['code', 'name', 'native_name']

class PatientSerializer(serializers.ModelSerializer):
    preferred_language_details = LanguageSerializer(source='preferred_language', read_only=True)
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ('updated_at',)
        
    def validate_user_id(self, value):
        # Ensure user_id is unique
        if Patient.objects.filter(user_id=value).exists():
            raise serializers.ValidationError("Patient profile already exists for this user.")
        return value

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_patient_name(self, obj):
        # Patient name comes from auth service via JWT token
        return f"Patient {obj.patient.user_id}"

class MedicalRecordSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalRecord
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_patient_name(self, obj):
        # Patient name comes from auth service via JWT token
        return f"Patient {obj.patient.user_id}"

class PrescriptionSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Prescription
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_patient_name(self, obj):
        # Patient name comes from auth service via JWT token
        return f"Patient {obj.patient.user_id}"

class PatientDashboardSerializer(serializers.ModelSerializer):
    upcoming_appointments = serializers.SerializerMethodField()
    active_prescriptions = serializers.SerializerMethodField()
    recent_records = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['id', 'user_id', 'upcoming_appointments', 'active_prescriptions', 'recent_records']
    
    def get_upcoming_appointments(self, obj):
        appointments = obj.appointments.filter(
            status__in=['SCHEDULED', 'CONFIRMED'],
            appointment_date__gte=timezone.now()
        ).order_by('appointment_date')[:5]
        return AppointmentSerializer(appointments, many=True).data
    
    def get_active_prescriptions(self, obj):
        prescriptions = obj.prescriptions.filter(is_active=True)
        return PrescriptionSerializer(prescriptions, many=True).data
    
    def get_recent_records(self, obj):
        records = obj.medical_records.all()[:5]
        return MedicalRecordSerializer(records, many=True).data