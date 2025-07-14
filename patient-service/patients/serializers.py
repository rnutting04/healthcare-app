from rest_framework import serializers


class LanguageSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)
    name = serializers.CharField(max_length=50)
    native_name = serializers.CharField(max_length=50)
    is_active = serializers.BooleanField(default=True)
    display_order = serializers.IntegerField(default=0)


class PatientSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField()
    date_of_birth = serializers.DateField()
    gender = serializers.ChoiceField(choices=['MALE', 'FEMALE', 'OTHER'])
    phone_number = serializers.CharField(max_length=20)
    address = serializers.CharField()
    emergency_contact_name = serializers.CharField(max_length=255)
    emergency_contact_phone = serializers.CharField(max_length=20)
    preferred_language_id = serializers.CharField(max_length=10, required=False, allow_null=True)
    preferred_language = LanguageSerializer(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AppointmentSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    patient = serializers.IntegerField(write_only=True)
    patient_id = serializers.IntegerField(read_only=True)
    clinician_id = serializers.IntegerField()
    clinician_name = serializers.CharField(max_length=255)
    appointment_date = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(default=30)
    status = serializers.ChoiceField(choices=[
        'SCHEDULED', 'CONFIRMED', 'IN_PROGRESS', 
        'COMPLETED', 'CANCELLED', 'NO_SHOW'
    ])
    reason = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class MedicalRecordSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    patient = serializers.IntegerField(write_only=True)
    patient_id = serializers.IntegerField(read_only=True)
    appointment_id = serializers.IntegerField(required=False, allow_null=True)
    clinician_id = serializers.IntegerField()
    clinician_name = serializers.CharField(max_length=255)
    record_type = serializers.ChoiceField(choices=[
        'CONSULTATION', 'LAB_RESULT', 'PRESCRIPTION',
        'IMAGING', 'PROCEDURE', 'VACCINATION'
    ])
    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    diagnosis = serializers.CharField(required=False, allow_blank=True)
    treatment = serializers.CharField(required=False, allow_blank=True)
    attachments = serializers.JSONField(default=list)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class PrescriptionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    patient = serializers.IntegerField(write_only=True)
    patient_id = serializers.IntegerField(read_only=True)
    medical_record_id = serializers.IntegerField(required=False, allow_null=True)
    clinician_id = serializers.IntegerField()
    clinician_name = serializers.CharField(max_length=255)
    medication_name = serializers.CharField(max_length=255)
    dosage = serializers.CharField(max_length=100)
    frequency = serializers.CharField(max_length=100)
    duration = serializers.CharField(max_length=100)
    instructions = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)


class PatientDashboardSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    patient_profile = PatientSerializer(required=False)
    upcoming_appointments = AppointmentSerializer(many=True, read_only=True)
    recent_records = MedicalRecordSerializer(many=True, read_only=True)
    active_prescriptions = PrescriptionSerializer(many=True, read_only=True)