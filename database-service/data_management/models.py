from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
import uuid


class Language(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=50)
    native_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'languages'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Role(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'roles'
    
    def __str__(self):
        return self.display_name

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    id = models.BigAutoField(primary_key=True)
    password = models.CharField(max_length=128)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='users', db_column='role_id')
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.email}"

class Patient(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField(unique=True, db_index=True)
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
    preferred_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True, db_column='preferred_language_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patients'
    
    def __str__(self):
        return f"Patient {self.user_id}"

# Clinician model removed as requested

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    ]
    
    id = models.BigAutoField(primary_key=True)
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
        managed = False
        managed = False  # Don't create migrations
    
    def __str__(self):
        return f"Appointment for Patient {self.patient.user_id} on {self.appointment_date}"

class MedicalRecord(models.Model):
    RECORD_TYPES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB_RESULT', 'Lab Result'),
        ('PRESCRIPTION', 'Prescription'),
        ('IMAGING', 'Imaging'),
        ('PROCEDURE', 'Procedure'),
        ('VACCINATION', 'Vaccination'),
    ]
    
    id = models.BigAutoField(primary_key=True)
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
        managed = False
        managed = False  # Don't create migrations
    
    def __str__(self):
        return f"{self.record_type} - {self.title}"

class Prescription(models.Model):
    id = models.BigAutoField(primary_key=True)
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
        managed = False
        managed = False  # Don't create migrations
    
    def __str__(self):
        return f"{self.medication_name} for Patient {self.patient.user_id}"

class CancerType(models.Model):
    cancer_type = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subtypes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cancer_types'
        indexes = [
            models.Index(fields=['cancer_type']),
            models.Index(fields=['parent']),
        ]
        
    def __str__(self):
        if self.parent:
            return f"{self.parent.cancer_type} - {self.cancer_type}"
        return self.cancer_type

class EventLog(models.Model):
    event_type = models.CharField(max_length=100)
    service = models.CharField(max_length=50)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'event_logs'
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['service']),
            models.Index(fields=['created_at']),
        ]


class UserEncryptionKey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='encryption_key')
    key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    rotated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_encryption_keys'
    
    def __str__(self):
        return f"Encryption key for {self.user.email}"


class FileMetadata(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, db_index=True)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    storage_path = models.CharField(max_length=500)
    is_encrypted = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'file_metadata'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user', '-uploaded_at']),
            models.Index(fields=['file_hash']),
        ]
    
    def __str__(self):
        return f"{self.filename} - {self.user.email}"


class FileAccessLog(models.Model):
    ACCESS_TYPE_CHOICES = [
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('delete', 'Delete'),
        ('view', 'View'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(FileMetadata, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPE_CHOICES)
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'file_access_logs'
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['file', '-accessed_at']),
            models.Index(fields=['user', '-accessed_at']),
        ]
    
    def __str__(self):
        return f"{self.access_type} - {self.file.filename} - {self.accessed_at}"


class RAGDocument(models.Model):
    file = models.OneToOneField(FileMetadata, on_delete=models.CASCADE, primary_key=True, related_name='rag_document')
    cancer_type = models.ForeignKey(CancerType, on_delete=models.CASCADE, related_name='documents')
    
    class Meta:
        db_table = 'rag_documents'
        indexes = [
            models.Index(fields=['cancer_type']),
        ]
    
    def __str__(self):
        return f"{self.file.filename} - {self.cancer_type}"


class RefreshToken(models.Model):
    id = models.BigAutoField(primary_key=True)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens', db_column='user_id')
    
    class Meta:
        db_table = 'refresh_tokens'
    
    def __str__(self):
        return f"Token for {self.user.email}"