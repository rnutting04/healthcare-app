# File Service

A secure file storage service with encryption and deduplication for the Healthcare Microservice System.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Data Flow](#data-flow)
- [API Endpoints](#api-endpoints)
- [Security Implementation](#security-implementation)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [Technical Details](#technical-details)
- [Error Handling](#error-handling)
- [Response Examples](#response-examples)

## Overview

The File Service is a microservice designed to handle secure file storage for the healthcare application. It provides end-to-end encryption, file deduplication, and comprehensive access control. The service acts as a secure vault for patient documents, medical records, and other sensitive healthcare files.

## Architecture

### System Components

1. **File Service (Django)** - Main service handling file operations
2. **Database Service** - Stores file metadata and encryption keys
3. **File Storage** - Encrypted file storage on disk
4. **Authentication Layer** - JWT-based authentication

### Directory Structure

```
file-service/
├── file_app/                # Main application module
│   ├── views.py            # API endpoints and business logic
│   ├── utils.py            # Encryption and file utilities
│   ├── urls.py             # URL routing
│   └── models.py           # (Uses database-service models)
├── file_service/           # Django project settings
│   ├── settings.py         # Configuration
│   └── urls.py             # Main URL configuration
├── media/                  # File storage directory
│   └── encrypted_files/    # Encrypted files organized by user ID
└── requirements.txt        # Python dependencies
```

## Features

- **File Deduplication**: Prevents duplicate files using SHA-256 hash comparison
- **User-Specific Encryption**: Each user has a unique Fernet encryption key
- **Secure Storage**: Files are encrypted before storage
- **Access Control**: Users can only access their own files
- **Audit Logging**: All file operations are logged with metadata
- **File Size Limits**: Configurable maximum file size (default: 100MB)
- **Soft Delete**: Files are marked as deleted but retained for recovery

## Data Flow

### File Upload Flow

1. **Authentication**: Client sends JWT token in Authorization header
2. **Validation**: Service validates token and extracts user ID
3. **Hash Calculation**: SHA-256 hash is calculated for the uploaded file
4. **Deduplication Check**: 
   - Service queries database for existing file with same hash
   - If duplicate found, upload is rejected with 409 Conflict
5. **Encryption Key Retrieval**:
   - Service requests user's encryption key from database service
   - If no key exists, a new one is generated and stored
6. **File Encryption**:
   - File is encrypted using Fernet symmetric encryption
   - Uses user-specific encryption key
7. **Storage**:
   - Encrypted file is saved to disk: `/media/encrypted_files/{user_id}/{file_id}.{ext}`
   - Directory structure ensures user isolation
8. **Metadata Storage**:
   - File metadata is sent to database service
   - Includes: filename, hash, size, mime type, storage path
9. **Access Logging**:
   - Upload event is logged with IP address and user agent

### File Download Flow

1. **Authentication**: JWT token validation
2. **Authorization**: 
   - Retrieve file metadata from database
   - Verify user owns the file
   - Check if file is not deleted
3. **Decryption**:
   - Retrieve user's encryption key
   - Read encrypted file from disk
   - Decrypt using Fernet
4. **Response**:
   - Return decrypted file with original filename
   - Set appropriate Content-Type header
5. **Access Logging**: Download event is logged

### File Deletion Flow

1. **Authentication & Authorization**: Same as download
2. **Soft Delete**: File is marked as deleted in database
3. **Physical Deletion**: Encrypted file is removed from disk
4. **Access Logging**: Deletion event is logged

## API Endpoints

### Upload File
```
POST /api/files/upload
Authorization: Bearer <JWT_TOKEN>
Content-Type: multipart/form-data

Body: file=<binary_data>
```

### Download File
```
GET /api/files/<file_id>
Authorization: Bearer <JWT_TOKEN>
```

### List User Files
```
GET /api/files/user
Authorization: Bearer <JWT_TOKEN>
```

### Delete File
```
DELETE /api/files/<file_id>/delete
Authorization: Bearer <JWT_TOKEN>
```

### Health Check
```
GET /api/health/
```

## Security Implementation

### Encryption Details

1. **Algorithm**: Fernet (symmetric encryption)
   - Based on AES 128-bit in CBC mode
   - HMAC using SHA256 for authentication
   - Timestamp for freshness

2. **Key Management**:
   - Each user has a unique encryption key
   - Keys are generated using Fernet.generate_key()
   - Keys are stored in database service
   - Keys are retrieved on-demand for each operation

3. **File Isolation**:
   - Files stored in user-specific directories
   - Directory structure: `/media/encrypted_files/{user_id}/`
   - OS-level permissions provide additional security

### Authentication & Authorization

1. **JWT Token Validation**:
   ```python
   payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
   ```

2. **User Verification**:
   - Extract user_id from JWT payload
   - Verify user owns the requested resource
   - All operations are user-scoped

3. **Service-to-Service Auth**:
   - Uses X-Service-Token header for database service calls
   - Ensures only authorized services can access metadata

### Deduplication Security

- Prevents storage of identical files
- Hash comparison happens before encryption
- Deduplication is global (across all users)
- Does not reveal file ownership information

## Setup Instructions

1. **Database Migration**: 
   ```bash
   # The file service uses the database service for metadata storage
   # Ensure database service is running and migrations are applied
   ```

2. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with appropriate values
   ```

3. **Start Service**:
   ```bash
   docker-compose up file-service
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Auto-generated |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Allowed host headers | `localhost,127.0.0.1` |
| `DATABASE_SERVICE_URL` | Database service endpoint | `http://database-service:8004` |
| `JWT_SECRET_KEY` | JWT signing key | Must match auth service |
| `FILE_STORAGE_PATH` | Encrypted file storage path | `/app/media/encrypted_files` |
| `MAX_FILE_SIZE_MB` | Maximum file size in MB | `100` |

## Technical Details

### File Hash Calculation

```python
def calculate_file_hash(file_data):
    sha256_hash = hashlib.sha256()
    for chunk in file_data.chunks():
        sha256_hash.update(chunk)
    return sha256_hash.hexdigest()
```

### Encryption Process

```python
def encrypt_file(file_data, encryption_key):
    fernet = Fernet(encryption_key)
    encrypted_data = fernet.encrypt(file_data)
    return encrypted_data
```

### Storage Structure

```
media/
└── encrypted_files/
    ├── 1/                    # User ID 1
    │   ├── uuid1.pdf        # Encrypted files
    │   └── uuid2.docx
    ├── 2/                    # User ID 2
    │   └── uuid3.jpg
    └── 3/                    # User ID 3
        └── uuid4.png
```

### Database Integration

The service communicates with the database service for:

1. **File Metadata Storage**:
   - File information (name, size, hash, mime type)
   - Storage path reference
   - Upload timestamp
   - Deletion status

2. **Encryption Key Management**:
   - User-specific encryption keys
   - Key generation and retrieval
   - Key rotation support (future feature)

3. **Access Logging**:
   - All file operations are logged
   - Includes: user, action, timestamp, IP, user agent
   - Success/failure status

## Error Handling

### Client Errors (4xx)

- **400 Bad Request**: No file provided, file too large
- **401 Unauthorized**: Invalid or missing JWT token
- **403 Forbidden**: User doesn't own the requested file
- **404 Not Found**: File doesn't exist or has been deleted
- **409 Conflict**: Duplicate file detected

### Server Errors (5xx)

- **500 Internal Server Error**: 
  - Encryption/decryption failure
  - Database service unavailable
  - File system errors

### Error Response Format

```json
{
    "success": false,
    "error": "Error type",
    "message": "Human-readable error message"
}
```

## Response Examples

### Upload Success
```json
{
    "success": true,
    "message": "File uploaded successfully",
    "file_id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "document.pdf",
    "uploaded_at": "2025-01-13T10:30:00Z",
    "size": 1048576,
    "mime_type": "application/pdf"
}
```

### Upload Rejection (Duplicate)
```json
{
    "success": false,
    "error": "Duplicate file",
    "message": "This file already exists in the system",
    "file_hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
}
```

### List Files Response
```json
{
    "success": true,
    "files": [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "filename": "medical_report.pdf",
            "size": 2048576,
            "mime_type": "application/pdf",
            "uploaded_at": "2025-01-13T10:30:00Z",
            "is_deleted": false
        }
    ],
    "count": 1
}
```

## Performance Considerations

1. **File Chunking**: Large files are processed in chunks to manage memory
2. **Async Operations**: Consider implementing async file operations for large files
3. **Caching**: Encryption keys could be cached (with appropriate TTL)
4. **Storage Optimization**: Implement file compression before encryption

## Future Enhancements

1. **File Versioning**: Track multiple versions of the same file
2. **Virus Scanning**: Integrate with antivirus service
3. **File Preview**: Generate thumbnails for images
4. **Bulk Operations**: Upload/download multiple files
5. **File Sharing**: Secure file sharing between users
6. **Encryption Key Rotation**: Periodic key rotation for enhanced security
7. **S3 Integration**: Option to store files in cloud storage