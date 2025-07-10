
from django.contrib import admin
from .models import Patient, Appointment, MedicalRecord, Prescription

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'phone_number', 'gender', 'created_at')
    list_filter = ('gender', 'created_at')
    search_fields = ('user_id', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'clinician_name', 'appointment_date', 'status', 'created_at')
    list_filter = ('status', 'appointment_date', 'created_at')
    search_fields = ('patient__user_id', 'clinician_name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'record_type', 'title', 'clinician_name', 'created_at')
    list_filter = ('record_type', 'created_at')
    search_fields = ('patient__user_id', 'title', 'clinician_name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'medication_name', 'clinician_name', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('patient__user_id', 'medication_name', 'clinician_name')
    readonly_fields = ('created_at',)