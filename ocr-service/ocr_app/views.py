"""Views for OCR service - ALL endpoints require authentication"""
import os
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from pathlib import Path
import uuid

from .decorators import handle_exceptions, require_auth
from .exceptions import ValidationError, FileProcessingError
from .services import get_ocr_service
from .gpu_detector import GPUDetector

logger = logging.getLogger(__name__)


@api_view(['POST'])
@handle_exceptions
@require_auth  # AUTHENTICATION REQUIRED
def submit_ocr_job(request):
    """Submit a file for OCR processing"""
    # Check if file was uploaded
    if 'file' not in request.FILES:
        raise ValidationError("No file provided")
    
    uploaded_file = request.FILES['file']
    
    # Validate file extension
    file_ext = Path(uploaded_file.name).suffix.lower()
    if file_ext not in settings.OCR_ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Invalid file type: {file_ext}. Allowed types: {', '.join(settings.OCR_ALLOWED_EXTENSIONS)}"
        )
    
    # Validate file size
    if uploaded_file.size > settings.OCR_MAX_FILE_SIZE_MB * 1024 * 1024:
        raise FileProcessingError(
            f"File too large: {uploaded_file.size / (1024*1024):.2f}MB > {settings.OCR_MAX_FILE_SIZE_MB}MB"
        )
    
    # Determine file type
    if file_ext in ['.txt', '.rtf']:
        file_type = 'text'
    elif file_ext == '.pdf':
        file_type = 'pdf'
    elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        file_type = 'image'
    else:
        raise ValidationError(f"Unsupported file type: {file_ext}")
    
    # Save file temporarily
    file_id = str(uuid.uuid4())
    file_path = os.path.join(settings.TEMP_FILE_PATH, f"{file_id}{file_ext}")
    
    try:
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Submit job for processing
        job_id = get_ocr_service().submit_job(
            file_path=file_path,
            file_name=uploaded_file.name,
            file_type=file_type,
            user_id=request.user_id,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({
            'success': True,
            'message': 'File submitted for OCR processing',
            'job_id': job_id,
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size,
            'file_type': file_type,
            'websocket_url': f'/ws/ocr/progress/{job_id}/'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise


@api_view(['GET'])
@handle_exceptions
@require_auth  # AUTHENTICATION REQUIRED
def get_job_status(request, job_id):
    """Get OCR job status"""
    job = get_ocr_service().get_job_status(job_id)
    
    if not job:
        return Response({
            'success': False,
            'message': 'Job not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Verify user owns the job
    if job.get('user_id') != request.user_id:
        return Response({
            'success': False,
            'message': 'Access denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Remove sensitive information
    job.pop('file_path', None)
    
    return Response({
        'success': True,
        'job': job
    })


@api_view(['GET'])
@handle_exceptions
@require_auth  # AUTHENTICATION REQUIRED
def get_job_result(request, job_id):
    """Get OCR job result (extracted text)"""
    job = get_ocr_service().get_job_status(job_id)
    
    if not job:
        return Response({
            'success': False,
            'message': 'Job not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Verify user owns the job
    if job.get('user_id') != request.user_id:
        return Response({
            'success': False,
            'message': 'Access denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if job.get('status') != 'completed':
        return Response({
            'success': False,
            'message': f"Job not completed. Current status: {job.get('status')}"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = job.get('result', {})
    
    return Response({
        'success': True,
        'job_id': job_id,
        'file_name': job.get('file_name'),
        'extracted_text': result.get('extracted_text', ''),
        'confidence_score': result.get('confidence_score', 0),
        'page_count': result.get('page_count', 0),
        'processing_time': result.get('processing_time', 0),
        'model_used': result.get('model_used', 'unknown'),
        'gpu_used': result.get('gpu_used', False)
    })


@api_view(['GET'])
@handle_exceptions
@require_auth  # AUTHENTICATION REQUIRED
def get_user_jobs(request):
    """Get user's OCR jobs"""
    limit = int(request.GET.get('limit', 10))
    limit = min(limit, 100)  # Cap at 100
    
    jobs = get_ocr_service().get_user_jobs(request.user_id, limit)
    
    # Remove sensitive information
    for job in jobs:
        job.pop('file_path', None)
    
    return Response({
        'success': True,
        'jobs': jobs,
        'count': len(jobs)
    })


@api_view(['POST'])
@handle_exceptions
@require_auth  # AUTHENTICATION REQUIRED
def cancel_job(request, job_id):
    """Cancel a pending or processing OCR job"""
    success = get_ocr_service().cancel_job(job_id, request.user_id)
    
    if success:
        return Response({
            'success': True,
            'message': 'Job cancelled successfully'
        })
    else:
        return Response({
            'success': False,
            'message': 'Unable to cancel job. Job may not exist, be owned by you, or already completed.'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@handle_exceptions
@require_auth  # AUTHENTICATION REQUIRED
def get_queue_stats(request):
    """Get OCR queue statistics"""
    stats = get_ocr_service().get_queue_stats()
    
    return Response({
        'success': True,
        'statistics': stats
    })


@api_view(['GET'])
@handle_exceptions
@require_auth  # AUTHENTICATION REQUIRED
def get_system_info(request):
    """Get system information including GPU status"""
    info = GPUDetector.get_system_info()
    
    return Response({
        'success': True,
        'system_info': info,
        'models': {
            'gpu_model': settings.OCR_MODEL_GPU,
            'cpu_model': settings.OCR_MODEL_CPU,
            'gpu_threshold_gb': settings.OCR_GPU_THRESHOLD
        }
    })


@api_view(['GET'])
@handle_exceptions
def health_check(request):
    """Health check endpoint - No authentication required for monitoring"""
    # Check Redis
    from .queue_manager import RedisQueueManager
    queue_manager = RedisQueueManager()
    redis_healthy = queue_manager.health_check()
    
    # Check if processing thread is running
    service = get_ocr_service()
    processing_healthy = service.processing_thread and service.processing_thread.is_alive()
    
    # Check GPU detection
    try:
        gpu_info = GPUDetector.get_system_info()
        gpu_detection_working = True
    except:
        gpu_detection_working = False
    
    all_healthy = redis_healthy and processing_healthy and gpu_detection_working
    
    return Response({
        'status': 'healthy' if all_healthy else 'unhealthy',
        'service': 'ocr-service',
        'timestamp': timezone.now().isoformat(),
        'checks': {
            'redis': redis_healthy,
            'processing_thread': processing_healthy,
            'gpu_detection': gpu_detection_working
        }
    }, status=200 if all_healthy else 503)