import jwt
import secrets
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .services import DatabaseService
import logging

logger = logging.getLogger(__name__)


def generate_access_token(user):
    """Generate JWT access token for user (user can be dict or object)"""
    if isinstance(user, dict):
        user_id = user.get('id')
        email = user.get('email')
        role_name = user.get('role', {}).get('name') if isinstance(user.get('role'), dict) else user.get('role_name')
    else:
        # Legacy support for model objects
        user_id = user.id
        email = user.email
        role_name = user.role.name
    
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role_name,
        'exp': timezone.now() + settings.JWT_ACCESS_TOKEN_LIFETIME,
        'iat': timezone.now(),
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def generate_refresh_token(user):
    """Generate refresh token for user (user can be dict or object)"""
    if isinstance(user, dict):
        user_id = user.get('id')
    else:
        user_id = user.id
    
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + settings.JWT_REFRESH_TOKEN_LIFETIME
    
    try:
        # Create refresh token via database service
        refresh_token = DatabaseService.create_refresh_token(
            user_id=user_id,
            token=token,
            expires_at=expires_at.isoformat()
        )
        return token
    except Exception as e:
        logger.error(f"Failed to create refresh token: {e}")
        raise


def verify_refresh_token(token):
    """Verify refresh token and return token data if valid"""
    try:
        token_data = DatabaseService.validate_refresh_token(token)
        if token_data and token_data.get('is_valid'):
            return token_data
        return None
    except Exception as e:
        logger.error(f"Failed to verify refresh token: {e}")
        return None


def invalidate_refresh_token(token):
    """Invalidate a specific refresh token"""
    try:
        DatabaseService.invalidate_refresh_token(token)
        return True
    except Exception as e:
        logger.error(f"Failed to invalidate refresh token: {e}")
        return False


def invalidate_all_user_tokens(user):
    """Invalidate all refresh tokens for a user"""
    if isinstance(user, dict):
        user_id = user.get('id')
    else:
        user_id = user.id
    
    try:
        DatabaseService.invalidate_user_tokens(user_id)
    except Exception as e:
        logger.error(f"Failed to invalidate user tokens: {e}")
        raise