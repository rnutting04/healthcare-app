from django.utils import translation
from django.conf import settings
from .services import DatabaseService
import logging

logger = logging.getLogger(__name__)

class UserLanguageMiddleware:
    """
    Middleware to set the user's preferred language for each request.
    This runs after JWTAuthenticationMiddleware, so we have user_id available.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip if no user is authenticated
        if not hasattr(request, 'user_id'):
            return self.get_response(request)
        
        # Try to get the user's preferred language
        try:
            patient = DatabaseService.get_patient_by_user_id(request.user_id)
            logger.info(f"Patient data for user {request.user_id}: {patient}")
            
            if patient and patient.get('preferred_language'):
                # Use the language code directly
                language_code = patient['preferred_language']
                logger.info(f"Setting language to: {language_code}")
                translation.activate(language_code)
                request.LANGUAGE_CODE = language_code
            else:
                # Use default language
                logger.info(f"No preferred language, using default: {settings.LANGUAGE_CODE}")
                translation.activate(settings.LANGUAGE_CODE)
                request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        except Exception as e:
            # Any error, use default
            logger.error(f"Error in language middleware: {e}")
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        
        response = self.get_response(request)
        
        # Set the Content-Language header
        response['Content-Language'] = translation.get_language()
        
        return response