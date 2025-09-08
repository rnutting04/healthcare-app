from __future__ import annotations
from typing import Any, Optional, Dict
import base64
import json
import logging
import hashlib

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.core.cache import cache
import requests

from patients.services import DatabaseService
from patients.utils import auth_headers_from_request

logger = logging.getLogger(__name__)
#create a Library instance to register the template tag
register = template.Library()

# --- Helper Functions ---
def _extract_lang_code(payload: Any) -> Optional[str]:
    """
    Finds and returns a language code from a single patient object.
    """
    #check if payload is a dictionary
    if not isinstance(payload, dict):
        return None

    #get the language code
    return payload.get("preferred_language_id")

def _jwt_payload_from_cookie(request) -> Dict[str, Any]:
    """
    Decodes the JWT from the 'access_token' cookie to read its data.
    IMPORTANT: This does NOT verify the token's signature. It's only for reading
    public information like the user ID. It should never be trusted for security decisions.
    """
    #get the token from the request's cookies
    token = getattr(request, "COOKIES", {}).get("access_token")
    #a valid JWT has three parts separated by two dots: header.payload.signature
    if not token or token.count(".") != 2:
        return {}
    try:
        #the data we want is the middle part of the token
        payload_b64 = token.split(".")[1]
        #the payload is Base64Url encoded
        #Base64 requires the length of the string to be a multiple of 4
        #so might need padding ('=') to be decoded correctly
        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)

        #decode the bytes into a UTF-8 string and then parse it as JSON
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return {}

def _get_user_id(request) -> Optional[int]:
    """
    Tries to find the current user's ID from multiple possible sources.
    1. A logged-in Django user object.
    2. Custom data attached to the request (e.g., by a middleware).
    3. The 'sub' (subject) or 'user_id' claim inside a JWT cookie.
    """
    # 1. Check for a standard, authenticated Django user.
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        try:
            return int(user.id)
        except Exception as e:
            logger.debug("Failed to get user id: %s", e)
            pass

    # 2. Check for user data injected by a middleware or gateway.
    user_data = getattr(request, "user_data", None)
    if isinstance(user_data, dict):
        for key in ("id", "user_id"):
            if key in user_data:
                try:
                    return int(user_data[key])
                except Exception as e:
                    logger.debug("Failed to find user data injected by a middleware or gateway: %s", e)
                    pass

    # 3. Decode the JWT from the cookie and check for an ID.
    payload = _jwt_payload_from_cookie(request)
    for key in ("sub", "user_id", "uid", "id"):
        if key in payload:
            try:
                return int(payload[key])
            except Exception as e:
                logger.debug("Failed to decode JWT payload from cookie: %s", e)
                continue

    return None

def _submit_translation(text: str, target_code: str, request) -> dict:
    """
    Sends the text to the external translation service API via a POST request.
    """
    base_url = getattr(settings, "CTRANS_API_BASE", "http://translation-service:8008/api")
    auth_headers = auth_headers_from_request(request)

    # API call with timeout of 2s to connect and 6s to get a response
    response = requests.post(
        f"{base_url}/translate",
        json={"text": text, "target_language": target_code},
        headers=auth_headers,
        timeout=(2, 6),
    )
    #raise an exception if the API returns an error or status (ex. 401 or 500)
    response.raise_for_status()
    #return the JSON response from the API
    return response.json()

def _resolve_lang_code(context) -> str:
    """
    Determine the target language code for the current user.
    Try DB via user_id; otherwise fall back to request.LANGUAGE_CODE or 'en'.
    """
    default_code = "en"
    request = context.get("request")
    if not request:
        return default_code

    user_id = _get_user_id(request)
    if user_id:
        try:
            patient_data = DatabaseService.get_patient_by_user_id(user_id)
            lang_code= _extract_lang_code(patient_data)
            if lang_code:
                return lang_code
        except Exception as e:
            # Log errors if the database call fails, but don't crash the page.
            logger.warning("ctrans: DB service error for user_id=%s: %s", user_id, e)

    #fallback: use the language Django detected from the request
    django_lang_code = getattr(request, "LANGUAGE_CODE", default_code)
    # And finally, inline the normalization logic for the fallback.
    return (django_lang_code or default_code)

# ---------------------------
# The template tag
# ---------------------------
@register.simple_tag(takes_context=True)
def ctrans(context, text: str):
    """
    This is the custom template tag itself.
    Usage in a template: {% load ctrans %} then {% ctrans "Text to translate" %}

    It determines the user's language and calls a translation service. If the
    translation is not ready immediately, it renders a placeholder that a
    frontend script can update later.
    """
    request = context.get("request")

    #figure out the target language
    code = _resolve_lang_code(context)

    #if the language is English, no translation is needed
    if code == "en":
        return _(text)

    #try to get a translation from the API
    #set pending lock to prevent other processess from duplicating 
    try:
        data = _submit_translation(text, code, request)
    except Exception as e:
        logger.warning("ctrans: submit failed (%s); falling back", e)
        return _(text)

    # Handle the API's responses
    # Case A: Translation was completed immediately (a cache hit on the service's side)
    if isinstance(data, dict) and data.get("status") == "completed":
        result = data.get("result")
        if result:
            return result
        return _(text)

    # Case B: Translation is pending, render the placeholder
    request_id = (data or {}).get("request_id")
    return _render_pending_placeholder(request_id=request_id, text=text)

def _render_pending_placeholder(request_id: str | None, text: str) -> str:
    """
    Renders the HTML placeholder using the direct data-ctrans-request-id attribute.
    """
    if not request_id:
        return _(text)

    text_length = len(_(text))
    estimated_width = text_length * 0.55 #adjust as needed

    return format_html(
        (
            '<span class="ctrans bg-gray-150 dark:bg-gray-300 rounded-md animate-pulse"'
            ' data-ctrans-status="pending"'
            ' data-ctrans-request-id="{}"'
            ' style="width: {}em; min-width: 2em; height: 1.2em; display: inline-block;">'
            '&nbsp;' # Non-breaking space to ensure element has content and height
            '</span>'
        ),
        request_id,
        mark_safe(str(estimated_width)), # Mark as safe to render the style attribute
    )