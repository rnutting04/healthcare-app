"""Authentication utilities for Patient service"""
import jwt
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_jwt_token(request):
    """
    Verify JWT token from request headers
    Returns: (payload, error_message)
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header:
            return None, "Authorization header missing"
        
        # Extract token from "Bearer <token>" format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None, "Invalid authorization header format"
        
        token = parts[1]
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Check if token has required fields
        if 'user_id' not in payload:
            return None, "Invalid token payload"
        
        return payload, None
        
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT validation error: {str(e)}")
        return None, "Invalid token"
    except Exception as e:
        logger.error(f"Unexpected error in JWT verification: {str(e)}")
        return None, "Authentication failed"


def verify_websocket_token(token):
    """
    Verify JWT token for WebSocket connections
    Returns: (payload, error_message)
    """
    try:
        if not token:
            return None, "Token missing"
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Check if token has required fields
        if 'user_id' not in payload:
            return None, "Invalid token payload"
        
        return payload, None
        
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError as e:
        logger.error(f"WebSocket JWT validation error: {str(e)}")
        return None, "Invalid token"
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket JWT verification: {str(e)}")
        return None, "Authentication failed"