from django.db import models
from django.utils import timezone

class Clinician(models.Model):
    SPECIALIZATION_CHOICES = [
        ('GENERAL', 'General Practitioner'),
        ('CARDIOLOGY', 'Cardiologist'),
        ('DERMATOLOGY', 'Dermatologist'),
        ('NEUROLOGY', 'Neurologist'),
        ('PEDIATRICS', 'Pediatrician'),
        ('PSYCHIATRY', 'Psychiatrist'),
        ('ORTHOPEDICS', 'Orthopedic Surgeon'),
        ('RADIOLOGY', 'Radiologist'),
        ('SURGERY', 'Surgeon'),
        ('OTHER', 'Other'),
    ]
    
    user_id = models.IntegerField(unique=True)
    email = models.EmailField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=20, choices=SPECIALIZATION_CHOICES)
    license_number = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20)
    office_address = models.TextField()
    years_of_experience = models.IntegerField()
    bio = models.TextField(blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'clinicians'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name} - {self.get_specialization_display()}"

class Schedule(models.Model):
    DAYS_OF_WEEK = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    ]
    
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'schedules'
        unique_together = ['clinician', 'day_of_week', 'start_time']
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.clinician} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

class PatientAssignment(models.Model):
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE, related_name='patient_assignments')
    patient_id = models.IntegerField()
    patient_name = models.CharField(max_length=255)
    assigned_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'patient_assignments'
        unique_together = ['clinician', 'patient_id']
        ordering = ['-assigned_date']
    
    def __str__(self):
        return f"{self.clinician} - {self.patient_name}"

class ClinicianAppointment(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    ]
    
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE, related_name='appointments')
    patient_id = models.IntegerField()
    patient_name = models.CharField(max_length=255)
    appointment_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    reason = models.TextField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'clinician_appointments'
        ordering = ['appointment_date']
    
    def __str__(self):
        return f"{self.clinician} - {self.patient_name} on {self.appointment_date}"

class MedicalNote(models.Model):
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE, related_name='medical_notes')
    appointment = models.ForeignKey(ClinicianAppointment, on_delete=models.CASCADE, null=True, blank=True)
    patient_id = models.IntegerField()
    patient_name = models.CharField(max_length=255)
    chief_complaint = models.TextField()
    history_of_present_illness = models.TextField()
    physical_examination = models.TextField()
    diagnosis = models.TextField()
    treatment_plan = models.TextField()
    follow_up = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_notes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note for {self.patient_name} by {self.clinician}"