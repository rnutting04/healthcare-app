from django.utils import translation
from django.conf import settings
from .models import Patient

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
            patient = Patient.objects.select_related('preferred_language').get(user_id=request.user_id)
            if patient.preferred_language:
                # Activate the user's preferred language
                translation.activate(patient.preferred_language.code)
                request.LANGUAGE_CODE = patient.preferred_language.code
            else:
                # Use default language
                translation.activate(settings.LANGUAGE_CODE)
                request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        except Patient.DoesNotExist:
            # User doesn't have a patient profile yet, use default
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        
        response = self.get_response(request)
        
        # Set the Content-Language header
        response['Content-Language'] = translation.get_language()
        
        return response