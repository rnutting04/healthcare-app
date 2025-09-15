from rest_framework import serializers
from typing import Dict, Any


class UserSerializer(serializers.Serializer):
    """Serializer for User data from database service"""
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    is_active = serializers.BooleanField(default=True)
    date_joined = serializers.DateTimeField(read_only=True)
    role_id = serializers.IntegerField(read_only=True)
    role_name = serializers.CharField(read_only=True)


class ClinicianRegistrationSerializer(serializers.Serializer):
    """Serializer for clinician registration"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    # Clinician-specific fields
    specialization_id = serializers.IntegerField()  # Foreign key to CancerType
    phone_number = serializers.CharField(max_length=20)
    
    def validate(self, data):
        """Validate registration data"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data


class ClinicianLoginSerializer(serializers.Serializer):
    """Serializer for clinician login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ClinicianSerializer(serializers.Serializer):
    """Serializer for Clinician data from database service"""
    id = serializers.IntegerField(read_only=True)
    user = UserSerializer(read_only=True)
    specialization = serializers.IntegerField()  # ID of CancerType
    specialization_detail = serializers.DictField(read_only=True)  # Detail from database
    phone_number = serializers.CharField(max_length=20)
    is_available = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ClinicianProfileUpdateSerializer(serializers.Serializer):
    """Serializer for updating clinician profile"""
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    phone_number = serializers.CharField(max_length=20, required=False)
    specialization_id = serializers.IntegerField(required=False)  # Foreign key to CancerType
    is_available = serializers.BooleanField(required=False)


class TokenSerializer(serializers.Serializer):
    """Serializer for JWT tokens"""
    access = serializers.CharField()
    refresh = serializers.CharField()


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for refresh token"""
    refresh = serializers.CharField()


class ClinicianDashboardSerializer(serializers.Serializer):
    """Serializer for clinician dashboard data"""
    user_id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()
    clinician_profile = ClinicianSerializer(required=False)
    
    # Dashboard stats (placeholder data for now)
    total_patients = serializers.IntegerField(default=0)
    today_appointments = serializers.IntegerField(default=0)
    pending_appointments = serializers.IntegerField(default=0)
    
    # Lists (will be empty for stub implementation)
    upcoming_appointments = serializers.ListField(child=serializers.DictField(), default=list)
    recent_patients = serializers.ListField(child=serializers.DictField(), default=list)


class PatientListSerializer(serializers.Serializer):
    """Serializer for patient list data"""
    id = serializers.IntegerField(read_only=True)
    user = UserSerializer(read_only=True, required=False)
    phone_number = serializers.CharField(max_length=20, allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)
    emergency_contact_name = serializers.CharField(max_length=255, allow_blank=True, required=False)
    emergency_contact_phone = serializers.CharField(max_length=20, allow_blank=True, required=False)
    date_of_birth = serializers.DateField(required=False)
    gender = serializers.CharField(max_length=10, required=False)
    created_at = serializers.DateTimeField(read_only=True)
    
    # Patient assignment details
    assignment = serializers.SerializerMethodField()
    
    def get_assignment(self, obj):
        """Get patient assignment details if available"""
        if isinstance(obj, dict) and 'assignment' in obj:
            assignment = obj['assignment']
            return {
                'cancer_subtype': assignment.get('cancer_subtype'),
                'cancer_subtype_name': assignment.get('cancer_subtype_name'),
                'notes': assignment.get('notes'),
                'assigned_at': assignment.get('created_at')
            }
        return None