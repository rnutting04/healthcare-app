"""Custom exceptions for OCR service"""


class OCRServiceException(Exception):
    """Base exception for OCR service"""
    def __init__(self, message, status_code=500, details=None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(OCRServiceException):
    """Validation error"""
    def __init__(self, message, details=None):
        super().__init__(message, status_code=400, details=details)


class AuthenticationError(OCRServiceException):
    """Authentication error"""
    def __init__(self, message, details=None):
        super().__init__(message, status_code=401, details=details)


class FileProcessingError(OCRServiceException):
    """File processing error"""
    def __init__(self, message, details=None):
        super().__init__(message, status_code=422, details=details)


class OCRProcessingError(OCRServiceException):
    """OCR processing error"""
    def __init__(self, message, details=None):
        super().__init__(message, status_code=500, details=details)


class QueueError(OCRServiceException):
    """Queue operation error"""
    def __init__(self, message, details=None):
        super().__init__(message, status_code=503, details=details)