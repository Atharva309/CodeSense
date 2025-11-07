import os
import hashlib
import base64
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# HTTP Bearer token
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Pre-hashes with SHA256 to handle passwords longer than bcrypt's 72-byte limit.
    The SHA256 digest (32 bytes) is base64 encoded (44 chars) to ensure it's under 72 bytes.
    """
    # Pre-hash with SHA256 to handle passwords longer than 72 bytes
    password_bytes = password.encode('utf-8')
    sha256_digest = hashlib.sha256(password_bytes).digest()  # 32 bytes
    # Base64 encode to get a safe string representation (44 characters = 44 bytes when UTF-8 encoded)
    sha256_base64 = base64.b64encode(sha256_digest).decode('utf-8')
    # Safety check: ensure the string is under 72 bytes when UTF-8 encoded
    sha256_bytes = sha256_base64.encode('utf-8')
    if len(sha256_bytes) > 72:
        # This should never happen, but truncate if it does
        sha256_base64 = sha256_base64[:72]
    # Use bcrypt directly to avoid passlib compatibility issues
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(sha256_base64.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Pre-hashes with SHA256 to match the hashing process.
    """
    # Pre-hash with SHA256 to match the hashing process
    password_bytes = plain_password.encode('utf-8')
    sha256_digest = hashlib.sha256(password_bytes).digest()  # 32 bytes
    # Base64 encode to match the hashing process
    sha256_base64 = base64.b64encode(sha256_digest).decode('utf-8')
    # Safety check: ensure the string is under 72 bytes when UTF-8 encoded
    sha256_bytes = sha256_base64.encode('utf-8')
    if len(sha256_bytes) > 72:
        # This should never happen, but truncate if it does
        sha256_base64 = sha256_base64[:72]
    # Use bcrypt directly to avoid passlib compatibility issues
    return bcrypt.checkpw(sha256_base64.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user exists and is active
    from app.repo import get_user_by_id
    user = get_user_by_id(int(user_id))
    
    if user is None or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Remove password_hash from user dict before returning
    user_dict = dict(user)
    user_dict.pop("password_hash", None)
    return user_dict

