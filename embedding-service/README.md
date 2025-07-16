# Embedding Service - Healthcare Microservice System

## Overview

The Embedding Service is a specialized microservice within the healthcare system that handles document processing and vector embedding generation using OpenAI's API. It enables intelligent document analysis, semantic search, and similarity matching across healthcare documents.

**Port**: 8007  
**Technology Stack**: Python/Django, OpenAI API, Threading, HTTP Client

## Core Functionality

### Primary Features
- **Document Processing**: Supports PDF, DOC, DOCX, and TXT files
- **Vector Embeddings**: Generates embeddings using OpenAI's text-embedding-ada-002 model
- **Semantic Search**: Enables similarity search across processed documents
- **Queue Management**: Asynchronous processing with threading and progress tracking
- **Duplicate Detection**: Hash-based deduplication prevents reprocessing

### Healthcare Use Cases
- Medical document analysis and processing
- Research paper and clinical documentation handling
- Knowledge base creation for medical information
- Similarity search for related cases, symptoms, treatments
- Clinical note processing and analysis

## API Endpoints

### Document Processing
```
POST /embeddings/process/
```
- Uploads and queues documents for embedding processing
- Validates file type (.pdf, .txt, .doc, .docx) and size (max 50MB)
- Returns queue position and task status

**Request**: Multipart form data with file upload  
**Response**: `{"status": "queued", "position": 1, "document_id": "uuid"}`

### Status Monitoring
```
GET /embeddings/status/
```
- Returns overall queue status and statistics
- Shows active, completed, and failed tasks

**Response**: `{"queue_size": 5, "active_tasks": 2, "completed": 150, "failed": 3}`

```
GET /embeddings/status/<document_id>/
```
- Returns specific document processing status
- Checks both queue and database for completion status

**Response**: `{"status": "completed", "progress": 100, "embeddings_count": 45}`

### Queue Management
```
GET /embeddings/queue/
```
- Returns current queue state with all items
- Shows position and processing status for each task

**Response**: `{"queue": [{"document_id": "uuid", "position": 1, "status": "processing"}]}`

### Search Functionality
```
POST /embeddings/search/
```
- Semantic search using query embeddings
- Returns similar documents with similarity scores

**Request**: `{"query": "diabetes treatment", "limit": 10}`  
**Response**: `{"results": [{"document_id": "uuid", "similarity": 0.85, "text": "..."}]}`

### User Embeddings
```
GET /embeddings/user/
```
- Returns paginated list of user's embeddings
- Supports pagination with page/limit parameters

**Query Parameters**: `?page=1&limit=20`  
**Response**: `{"results": [...], "count": 100, "next": "..."}`

## Architecture

### Service Components

#### 1. QueueManager (Singleton Pattern)
- **Location**: `api/queue_manager.py`
- **Purpose**: Manages FIFO queue for embedding tasks
- **Features**:
  - Thread-safe queue operations
  - Priority support for urgent tasks
  - Progress tracking and statistics
  - Worker thread management (default: 3 concurrent workers)

#### 2. EmbeddingGenerator
- **Location**: `api/embedding_generator.py`
- **Purpose**: Handles OpenAI API integration
- **Features**:
  - Retry logic with exponential backoff
  - Rate limit handling
  - Batch processing optimization
  - Token management for text chunking

#### 3. DocumentProcessor
- **Location**: `api/document_processor.py`
- **Purpose**: Extracts text from various document formats
- **Features**:
  - Multi-format support (PDF, DOCX, TXT)
  - Hash-based duplicate detection
  - Intelligent text chunking
  - Metadata extraction

#### 4. DatabaseClient
- **Location**: `api/database_client.py`
- **Purpose**: Communicates with database service
- **Features**:
  - HTTP-based service communication
  - Service token authentication
  - Embedding storage and retrieval
  - Similarity search operations

### Processing Workflow

```
1. File Upload → Validation → Queue Addition
2. Queue → Worker Thread → Document Processing
3. Text Extraction → Chunking → Embedding Generation
4. Database Storage → Cleanup → Status Update
```

#### Detailed Processing Steps

1. **File Upload and Validation**
   - File type validation (.pdf, .txt, .doc, .docx)
   - Size validation (max 50MB)
   - Temporary storage in `temp_uploads/`

2. **Queue Processing**
   - SHA256 hash calculation for duplicate detection
   - Queue position assignment
   - Worker thread allocation

3. **Document Processing**
   - Format-specific text extraction
   - Text chunking for optimal embedding size
   - Progress tracking and status updates

4. **Embedding Generation**
   - OpenAI API calls with retry logic
   - Batch processing for efficiency
   - Token limit management

5. **Database Storage**
   - Embedding vectors and metadata storage
   - Document information persistence
   - User association and permissions

6. **Cleanup**
   - Temporary file deletion
   - Queue status updates
   - Error logging and reporting

## Authentication and Security

### Multi-layered Authentication
- **JWT Authentication**: Validates tokens with auth service
- **Service Token Authentication**: Internal service communication
- **Custom Permissions**: `IsAuthenticatedCustom` class in `api/permissions.py`

### Security Features
- Environment variable based configuration
- File type and size validation
- Service token for database communication
- Request timeout handling
- CORS configuration for allowed origins
- Comprehensive error logging

## Configuration

### Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=text-embedding-ada-002
OPENAI_MAX_TOKENS_PER_CHUNK=2000

# Queue Configuration
MAX_CONCURRENT_EMBEDDINGS=3
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY=1

# File Configuration
MAX_FILE_SIZE=52428800  # 50MB in bytes
ALLOWED_FILE_TYPES=.pdf,.txt,.doc,.docx
UPLOAD_DIR=temp_uploads

# Service URLs
DATABASE_SERVICE_URL=http://localhost:8004
AUTH_SERVICE_URL=http://localhost:8001

# Security
JWT_SECRET_KEY=your_jwt_secret_here
SERVICE_TOKEN=your_service_token_here

# Django Settings
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### Django Settings
- **Location**: `embedding_service/settings.py`
- **Key Areas**:
  - Database connection to PostgreSQL
  - JWT authentication configuration
  - CORS settings for frontend integration
  - Logging configuration
  - Static files and media handling

## Database Integration

### Communication with Database Service
- **Protocol**: HTTP REST API
- **Authentication**: X-Service-Token header
- **Endpoints Used**:
  - `POST /embeddings/` - Store embeddings
  - `GET /embeddings/user/<user_id>/` - Retrieve user embeddings
  - `POST /embeddings/search/` - Similarity search
  - `GET /embeddings/document/<doc_id>/` - Document status

### Data Models
Embeddings are stored in the database service with:
- Document metadata (filename, file_type, file_size)
- User association and permissions
- Embedding vectors and text chunks
- Processing timestamps and status
- Hash values for duplicate detection

## Performance and Scalability

### Performance Features
- **Asynchronous Processing**: Non-blocking document processing
- **Concurrent Workers**: Multiple embedding generation threads
- **Batch Processing**: Efficient handling of multiple text chunks
- **Caching**: Duplicate detection prevents reprocessing
- **Progress Tracking**: Real-time status updates

### Scalability Considerations
- **Horizontal Scaling**: Multiple service instances possible
- **Queue Distribution**: Can be enhanced with external queue systems (Redis, RabbitMQ)
- **Database Sharding**: Embedding storage can be distributed
- **Load Balancing**: Nginx proxy for multiple instances

## Error Handling and Monitoring

### Error Handling
- **Retry Logic**: Exponential backoff for API failures
- **Graceful Degradation**: Continues processing other documents
- **Detailed Logging**: Comprehensive error tracking
- **Status Reporting**: Clear error messages in API responses

### Monitoring Capabilities
- **Health Check**: `/health/` endpoint for service health
- **Queue Statistics**: Processing metrics and performance data
- **Progress Tracking**: Real-time task progress
- **Error Reporting**: Failed task tracking and analysis

## Development and Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver 0.0.0.0:8007
```

### Docker Deployment
```dockerfile
# Dockerfile included in service directory
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8007
CMD ["python", "manage.py", "runserver", "0.0.0.0:8007"]
```

### Integration with Healthcare System
- **Service Discovery**: Registered with nginx load balancer
- **Database Service**: Stores embeddings and metadata
- **Auth Service**: User authentication and authorization
- **File Service**: May receive documents from file uploads
- **Other Services**: Can be integrated for document analysis

## File Processing Details

### Supported Formats
- **PDF**: Uses PyPDF2 for text extraction
- **DOCX**: Uses python-docx for Word document processing
- **TXT**: Direct text file reading
- **DOC**: Handled through docx library compatibility

### Processing Features
- **Text Chunking**: Intelligent splitting for optimal embedding (max 2000 tokens)
- **Hash-based Deduplication**: SHA256 hashing prevents duplicate processing
- **Metadata Extraction**: Stores file information and processing details
- **Progress Reporting**: Real-time updates during processing

## API Response Examples

### Successful Document Processing
```json
{
  "status": "success",
  "message": "Document queued for processing",
  "data": {
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "queue_position": 1,
    "estimated_processing_time": "2-3 minutes"
  }
}
```

### Search Results
```json
{
  "status": "success",
  "results": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "similarity_score": 0.85,
      "text_chunk": "Diabetes treatment involves...",
      "metadata": {
        "filename": "diabetes_guide.pdf",
        "page": 15,
        "chunk_index": 3
      }
    }
  ],
  "total_results": 25,
  "processing_time": "0.34s"
}
```

## Troubleshooting

### Common Issues

1. **OpenAI API Errors**
   - Check API key validity
   - Verify rate limits and quotas
   - Review token limits per request

2. **Queue Processing Delays**
   - Monitor concurrent worker settings
   - Check database service connectivity
   - Review file size and complexity

3. **Database Connection Issues**
   - Verify database service URL
   - Check service token authentication
   - Review network connectivity

4. **File Upload Failures**
   - Verify file type and size limits
   - Check upload directory permissions
   - Review temporary storage space

### Logging and Debugging
- **Log Location**: Console output and Django logging
- **Debug Mode**: Set `DEBUG=True` in environment
- **Error Tracking**: Comprehensive error logging with stack traces
- **Performance Monitoring**: Queue statistics and processing metrics

## Future Enhancements

### Planned Features
- **Vector Database Integration**: Direct integration with specialized vector databases
- **Advanced Search**: Hybrid search combining semantic and keyword search
- **Batch Upload**: Multiple file upload and processing
- **Real-time Notifications**: WebSocket support for real-time updates
- **Advanced Analytics**: Document analysis and insights
- **Multi-language Support**: Processing documents in multiple languages

### Technical Improvements
- **Caching Layer**: Redis integration for embedding caching
- **Queue Persistence**: Persistent queue storage for reliability
- **Microservice Mesh**: Service mesh integration for better orchestration
- **Monitoring**: Comprehensive monitoring and alerting system
- **Auto-scaling**: Automatic scaling based on queue size and load

## Contributing

### Development Guidelines
- Follow Django best practices
- Implement comprehensive error handling
- Write unit tests for new features
- Document API changes
- Follow security best practices for healthcare data

### Testing
```bash
# Run unit tests
python manage.py test

# Run integration tests
python manage.py test api.tests.integration

# Run performance tests
python manage.py test api.tests.performance
```

This embedding service provides a robust foundation for intelligent document processing and semantic search within the healthcare microservice system, enabling advanced AI-powered features while maintaining security and performance standards appropriate for healthcare applications.