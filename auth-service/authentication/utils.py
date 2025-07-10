import jwt
import secrets
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import RefreshToken

def generate_access_token(user):
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role.name,
        'exp': timezone.now() + settings.JWT_ACCESS_TOKEN_LIFETIME,
        'iat': timezone.now(),
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token

def generate_refresh_token(user):
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + settings.JWT_REFRESH_TOKEN_LIFETIME
    
    refresh_token = RefreshToken.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )
    
    return refresh_token.token

def verify_refresh_token(token):
    try:
        refresh_token = RefreshToken.objects.get(token=token, is_active=True)
        
        if refresh_token.expires_at < timezone.now():
            refresh_token.is_active = False
            refresh_token.save()
            return None
        
        return refresh_token
    except RefreshToken.DoesNotExist:
        return None

def invalidate_refresh_token(token):
    try:
        refresh_token = RefreshToken.objects.get(token=token)
        refresh_token.is_active = False
        refresh_token.save()
        return True
    except RefreshToken.DoesNotExist:
        return False

def invalidate_all_user_tokens(user):
    RefreshToken.objects.filter(user=user, is_active=True).update(is_active=False)