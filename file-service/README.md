# File Service

A secure file storage service with encryption and deduplication for the Healthcare Microservice System.

## Features

- **File Deduplication**: Rejects duplicate files based on SHA-256 hash
- **User-Specific Encryption**: Each user has a unique encryption key
- **Secure Storage**: Files are encrypted before storage using Fernet encryption
- **Access Control**: Users can only access their own files
- **Audit Logging**: All file operations are logged for security auditing

## API Endpoints

- `POST /api/files/upload` - Upload a new file
- `GET /api/files/<file_id>` - Download a file
- `GET /api/files/user` - List all files for authenticated user
- `DELETE /api/files/<file_id>/delete` - Delete a file
- `GET /api/health/` - Health check endpoint

## Setup Instructions

1. **Database Migration**: Copy the migration file to database-service:
   ```bash
   docker cp file-service/0002_file_models.py healthcare-app_database-service_1:/app/data_management/migrations/
   ```

2. **Run Migrations**: Execute in the database-service container:
   ```bash
   docker exec -it healthcare-app_database-service_1 python manage.py migrate
   ```

3. **Start Service**: The service will start automatically with docker-compose

## Environment Variables

- `DATABASE_SERVICE_URL`: URL of the database service
- `JWT_SECRET_KEY`: Secret key for JWT token verification
- `FILE_STORAGE_PATH`: Path for storing encrypted files
- `MAX_FILE_SIZE_MB`: Maximum allowed file size in MB (default: 100)

## Security Features

- Files are encrypted using user-specific keys
- Deduplication prevents storage of identical files
- JWT authentication required for all operations
- Comprehensive access logging
- Isolated user data - compromised key only affects one user

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
    "file_hash": "abc123..."
}
```