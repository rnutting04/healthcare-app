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

class Clinician(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='clinician_profile')
    specialization = models.ForeignKey(
        'CancerType', 
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        limit_choices_to={'parent__isnull': True},  # Only parent cancer types
        related_name='clinicians'
    )
    phone_number = models.CharField(max_length=20, blank=True, default='')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'clinicians'
    
    def __str__(self):
        specialization_name = self.specialization.cancer_type if self.specialization else "No specialization"
        return f"Dr. {self.user.first_name} {self.user.last_name} - {specialization_name}"

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

class MedicalRecordType(models.Model):
    """
    Predefined types of medical records that don't change.
    """
    id = models.BigAutoField(primary_key=True)
    type_name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'medical_record_types'
        ordering = ['type_name']
    
    def __str__(self):
        return self.type_name


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


class PatientAssignment(models.Model):
    id = models.BigAutoField(primary_key=True)
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='assignment')
    cancer_subtype = models.ForeignKey(
        CancerType, 
        on_delete=models.PROTECT,
        limit_choices_to={'parent__isnull': False},  # Only subtypes (have parent)
        related_name='patient_assignments'
    )
    assigned_clinician = models.ForeignKey(
        Clinician,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_patients'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='patient_assignments_updated'
    )
    
    class Meta:
        db_table = 'patient_assignments'
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['assigned_clinician']),
            models.Index(fields=['cancer_subtype']),
        ]
    
    def __str__(self):
        return f"Assignment for Patient {self.patient.id} - {self.cancer_subtype.cancer_type}"


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


class MedicalRecord(models.Model):
    """
    Medical records linking files to patients with record types.
    Uses composite primary key of file, patient, and record type.
    """
    file = models.OneToOneField(FileMetadata, on_delete=models.CASCADE, primary_key=True, related_name='medical_record')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    medical_record_type = models.ForeignKey(MedicalRecordType, on_delete=models.PROTECT, related_name='medical_records')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_medical_records')
    # Store the encryption key encrypted with a master key (for emergency access)
    record_encryption_key = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'medical_records'
        unique_together = [['file', 'patient', 'medical_record_type']]
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['medical_record_type']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Medical Record: {self.file.filename} - Patient {self.patient.id} - {self.medical_record_type.type_name}"


class MedicalRecordAccess(models.Model):
    """
    Grants access to medical records for specific users.
    The record's encryption key is encrypted with each user's personal key.
    """
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='access_grants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medical_record_access')
    # The medical record's encryption key, encrypted with this user's personal key
    encrypted_access_key = models.TextField()
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='access_granted_by')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'medical_record_access'
        unique_together = [['medical_record', 'user']]
        indexes = [
            models.Index(fields=['user', '-granted_at']),
            models.Index(fields=['medical_record', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} access to {self.medical_record}"
    
    @property
    def is_active(self):
        """Check if access is currently active"""
        from django.utils import timezone
        now = timezone.now()
        if self.revoked_at and self.revoked_at <= now:
            return False
        if self.expires_at and self.expires_at <= now:
            return False
        return True


# RAG Embedding models
class RAGEmbedding(models.Model):
    """Store document embeddings for RAG system with PGVector"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(RAGDocument, on_delete=models.CASCADE, related_name='embeddings')
    chunk_index = models.IntegerField()
    chunk_text = models.TextField()
    embedding = models.JSONField()  # Will be handled as vector in queries
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rag_embeddings'
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
            models.Index(fields=['created_at']),
        ]
        unique_together = [['document', 'chunk_index']]
    
    def __str__(self):
        return f"Embedding {self.chunk_index} for {self.document.file.filename}"


class RAGEmbeddingJob(models.Model):
    """Track embedding processing jobs"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(RAGDocument, on_delete=models.CASCADE, related_name='embedding_jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'rag_embedding_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['document']),
        ]
    
    def __str__(self):
        return f"Job {self.id} - {self.status}"