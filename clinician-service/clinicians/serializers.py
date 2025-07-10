from rest_framework import serializers
from django.utils import timezone
from .models import Clinician, Schedule, PatientAssignment, ClinicianAppointment, MedicalNote

class ClinicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinician
        fields = '__all__'
        read_only_fields = ('user_id', 'created_at', 'updated_at')

class ScheduleSerializer(serializers.ModelSerializer):
    clinician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Schedule
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.first_name} {obj.clinician.last_name}"

class PatientAssignmentSerializer(serializers.ModelSerializer):
    clinician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientAssignment
        fields = '__all__'
        read_only_fields = ('assigned_date',)
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.first_name} {obj.clinician.last_name}"

class ClinicianAppointmentSerializer(serializers.ModelSerializer):
    clinician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicianAppointment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.first_name} {obj.clinician.last_name}"

class MedicalNoteSerializer(serializers.ModelSerializer):
    clinician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalNote
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.first_name} {obj.clinician.last_name}"

class ClinicianDashboardSerializer(serializers.ModelSerializer):
    today_appointments = serializers.SerializerMethodField()
    upcoming_appointments = serializers.SerializerMethodField()
    active_patients = serializers.SerializerMethodField()
    weekly_schedule = serializers.SerializerMethodField()
    
    class Meta:
        model = Clinician
        fields = ['id', 'user_id', 'first_name', 'last_name', 'specialization',
                 'today_appointments', 'upcoming_appointments', 'active_patients', 'weekly_schedule']
    
    def get_today_appointments(self, obj):
        today = timezone.now().date()
        appointments = obj.appointments.filter(
            appointment_date__date=today,
            status__in=['SCHEDULED', 'CONFIRMED']
        ).order_by('appointment_date')
        return ClinicianAppointmentSerializer(appointments, many=True).data
    
    def get_upcoming_appointments(self, obj):
        appointments = obj.appointments.filter(
            appointment_date__gt=timezone.now(),
            status__in=['SCHEDULED', 'CONFIRMED']
        ).order_by('appointment_date')[:10]
        return ClinicianAppointmentSerializer(appointments, many=True).data
    
    def get_active_patients(self, obj):
        return obj.patient_assignments.filter(is_active=True).count()
    
    def get_weekly_schedule(self, obj):
        schedules = obj.schedules.filter(is_active=True)
        return ScheduleSerializer(schedules, many=True).data