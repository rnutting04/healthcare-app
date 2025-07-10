from django.db import models
from django.utils import timezone

class Language(models.Model):
    """Supported languages for the application"""
    code = models.CharField(max_length=10, unique=True, primary_key=True)
    name = models.CharField(max_length=50)
    native_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'languages'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.native_name})"

class Patient(models.Model):
    # Reference to auth service user - primary identifier
    user_id = models.IntegerField(unique=True, db_index=True)
    
    # Patient-specific information only
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other')
    ])
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    emergency_contact_name = models.CharField(max_length=255)
    emergency_contact_phone = models.CharField(max_length=20)
    
    # Language preference
    preferred_language = models.ForeignKey(
        Language, 
        on_delete=models.SET_NULL,
        related_name='patients',
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField()  # Set from auth service's date_joined
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patients'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Patient ID: {self.user_id}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    clinician_id = models.IntegerField()
    clinician_name = models.CharField(max_length=255)
    appointment_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    reason = models.TextField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointments'
        ordering = ['appointment_date']
    
    def __str__(self):
        return f"Appointment for {self.patient} on {self.appointment_date}"

class MedicalRecord(models.Model):
    RECORD_TYPES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB_RESULT', 'Lab Result'),
        ('PRESCRIPTION', 'Prescription'),
        ('IMAGING', 'Imaging'),
        ('PROCEDURE', 'Procedure'),
        ('VACCINATION', 'Vaccination'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    clinician_id = models.IntegerField()
    clinician_name = models.CharField(max_length=255)
    record_type = models.CharField(max_length=20, choices=RECORD_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    diagnosis = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    attachments = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_records'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.record_type} - {self.title}"

class Prescription(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, null=True, blank=True)
    clinician_id = models.IntegerField()
    clinician_name = models.CharField(max_length=255)
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'prescriptions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.medication_name} for {self.patient}"