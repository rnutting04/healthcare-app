import os
import jwt  # pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Bearer auth extractor
auth_scheme = HTTPBearer(auto_error=False)

# Config via env
JWT_ALGO = os.getenv("JWT_ALGO", "HS256")        # HS256 or RS256, etc.
JWT_SECRET = os.getenv("JWT_SECRET_KEY")             # used for HS*

def _decode_jwt(token: str) -> dict:
    try:
        if not JWT_SECRET:
            raise HTTPException(status_code=500, detail="JWT_SECRET not set")
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGO],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_jwt(creds: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """FastAPI dependency: ensures a valid Bearer token is present."""
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization")
    claims = _decode_jwt(creds.credentials)
    # return whatever you want downstream (token for forwarding, plus claims)
    return {"token": creds.credentials, "claims": claims}
