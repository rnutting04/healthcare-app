"""Custom exceptions for RAG embedding service"""
from rest_framework import status


class RAGServiceException(Exception):
    """Base exception for RAG service"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "An error occurred in the RAG service"
    
    def __init__(self, message=None, details=None):
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class AuthenticationError(RAGServiceException):
    """Authentication related errors"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "Authentication failed"


class ValidationError(RAGServiceException):
    """Validation related errors"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Validation failed"


class DocumentNotFoundError(RAGServiceException):
    """Document not found errors"""
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Document not found"


class ProcessingError(RAGServiceException):
    """Document processing errors"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "Failed to process document"


class ExternalServiceError(RAGServiceException):
    """External service communication errors"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "External service unavailable"


class QueueError(RAGServiceException):
    """Queue operation errors"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "Queue operation failed"