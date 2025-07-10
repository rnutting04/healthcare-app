from django.contrib import admin
from .models import Clinician, Schedule, PatientAssignment, ClinicianAppointment, MedicalNote

@admin.register(Clinician)
class ClinicianAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'specialization', 'license_number', 'is_available', 'created_at')
    list_filter = ('specialization', 'is_available', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'license_number')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'day_of_week', 'start_time', 'end_time', 'is_active')
    list_filter = ('day_of_week', 'is_active')
    search_fields = ('clinician__first_name', 'clinician__last_name')
    readonly_fields = ('created_at',)

@admin.register(PatientAssignment)
class PatientAssignmentAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'patient_name', 'assigned_date', 'is_active')
    list_filter = ('is_active', 'assigned_date')
    search_fields = ('clinician__first_name', 'clinician__last_name', 'patient_name')
    readonly_fields = ('assigned_date',)

@admin.register(ClinicianAppointment)
class ClinicianAppointmentAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'patient_name', 'appointment_date', 'status', 'created_at')
    list_filter = ('status', 'appointment_date', 'created_at')
    search_fields = ('clinician__first_name', 'clinician__last_name', 'patient_name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(MedicalNote)
class MedicalNoteAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'patient_name', 'chief_complaint', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('clinician__first_name', 'clinician__last_name', 'patient_name', 'chief_complaint')
    readonly_fields = ('created_at', 'updated_at')