from django.contrib import admin
from .models import User, Patient, Clinician, Appointment, MedicalRecord, Prescription, EventLog

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'get_email', 'gender', 'blood_type', 'created_at')
    list_filter = ('gender', 'blood_type')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_full_name.short_description = 'Name'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

@admin.register(Clinician)
class ClinicianAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'specialization', 'license_number', 'is_available', 'created_at')
    list_filter = ('specialization', 'is_available')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'license_number')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_full_name(self, obj):
        return f"Dr. {obj.user.first_name} {obj.user.last_name}"
    get_full_name.short_description = 'Name'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'get_clinician_name', 'appointment_date', 'status', 'created_at')
    list_filter = ('status', 'appointment_date')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 
                    'clinician__user__first_name', 'clinician__user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'appointment_date'
    
    def get_patient_name(self, obj):
        return f"{obj.patient.user.first_name} {obj.patient.user.last_name}"
    get_patient_name.short_description = 'Patient'
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.user.first_name} {obj.clinician.user.last_name}"
    get_clinician_name.short_description = 'Clinician'

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_patient_name', 'get_clinician_name', 'record_type', 'created_at')
    list_filter = ('record_type', 'created_at')
    search_fields = ('title', 'patient__user__first_name', 'patient__user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    def get_patient_name(self, obj):
        return f"{obj.patient.user.first_name} {obj.patient.user.last_name}"
    get_patient_name.short_description = 'Patient'
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.user.first_name} {obj.clinician.user.last_name}"
    get_clinician_name.short_description = 'Clinician'

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('medication_name', 'get_patient_name', 'get_clinician_name', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('medication_name', 'patient__user__first_name', 'patient__user__last_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'start_date'
    
    def get_patient_name(self, obj):
        return f"{obj.patient.user.first_name} {obj.patient.user.last_name}"
    get_patient_name.short_description = 'Patient'
    
    def get_clinician_name(self, obj):
        return f"Dr. {obj.clinician.user.first_name} {obj.clinician.user.last_name}"
    get_clinician_name.short_description = 'Clinician'

@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'service', 'created_at')
    list_filter = ('event_type', 'service', 'created_at')
    search_fields = ('event_type', 'service')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'