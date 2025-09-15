"""Decorators for common patterns in OCR service"""
import functools
import logging
from rest_framework.response import Response
from .exceptions import AuthenticationError, OCRServiceException

logger = logging.getLogger(__name__)


def handle_exceptions(func):
    """Decorator to handle exceptions in views"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OCRServiceException as e:
            logger.error(f"{func.__name__} failed: {e.message}", exc_info=True)
            return Response({
                'success': False,
                'error': e.__class__.__name__,
                'message': e.message,
                'details': e.details
            }, status=e.status_code)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'UnexpectedError',
                'message': 'An unexpected error occurred'
            }, status=500)
    return wrapper


def require_auth(func):
    """Decorator to require authentication"""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        # Import here to avoid circular imports
        from .auth import verify_jwt_token
        
        payload, error = verify_jwt_token(request)
        if error:
            raise AuthenticationError(error)
        
        # Add user info to request
        request.user_payload = payload
        request.user_id = payload.get('user_id')
        
        return func(request, *args, **kwargs)
    return wrapper