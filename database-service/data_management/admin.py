from django.contrib import admin
from .models import User, Patient, Clinician, EventLog, CancerType

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'gender', 'phone_number', 'created_at')
    list_filter = ('gender',)
    search_fields = ('user_id', 'phone_number', 'emergency_contact_name')
    readonly_fields = ('created_at', 'updated_at')
    
    def __str__(self, obj):
        return f"Patient ID: {obj.user_id}"

@admin.register(Clinician)
class ClinicianAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'get_specialization', 'phone_number', 'is_available', 'created_at')
    list_filter = ('specialization', 'is_available')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_full_name(self, obj):
        return f"Dr. {obj.user.first_name} {obj.user.last_name}"
    get_full_name.short_description = 'Name'
    
    def get_specialization(self, obj):
        return obj.specialization.cancer_type if obj.specialization else 'Not specified'
    get_specialization.short_description = 'Specialization'

@admin.register(CancerType)
class CancerTypeAdmin(admin.ModelAdmin):
    list_display = ('cancer_type', 'parent', 'description', 'created_at')
    list_filter = ('parent', 'created_at')
    search_fields = ('cancer_type', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('cancer_type',)

@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'service', 'created_at')
    list_filter = ('event_type', 'service', 'created_at')
    search_fields = ('event_type', 'service')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'