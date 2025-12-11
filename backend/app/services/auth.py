"""Authentication service for JWT-based auth."""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.user_service import user_db
from app.models.user import UserCreate, UserResponse, Token, TokenData

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-figma-diff-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# HTTP Bearer token
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        
        if user_id is None:
            return None
        
        return TokenData(user_id=user_id, email=email)
    except JWTError:
        return None


def register_user(user_data: UserCreate) -> Optional[UserResponse]:
    """Register a new user."""
    # Hash the password
    password_hash = get_password_hash(user_data.password)
    
    # Generate user ID
    user_id = str(uuid.uuid4())
    
    # Create user in database
    success = user_db.create_user(
        user_id=user_id,
        email=user_data.email,
        password_hash=password_hash,
        full_name=user_data.full_name
    )
    
    if not success:
        return None  # Email already exists
    
    # Return user response
    return UserResponse(
        id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        is_active=True,
        created_at=datetime.utcnow()
    )


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate a user by email and password."""
    user = user_db.get_user_by_email(email)
    
    if not user:
        return None
    
    if not verify_password(password, user["password_hash"]):
        return None
    
    if not user.get("is_active", True):
        return None
    
    return user


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[UserResponse]:
    """Get current user from JWT token. Returns None if not authenticated."""
    if not credentials:
        return None
    
    token_data = decode_token(credentials.credentials)
    
    if not token_data or not token_data.user_id:
        return None
    
    user = user_db.get_user_by_id(token_data.user_id)
    
    if not user:
        return None
    
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name"),
        is_active=bool(user.get("is_active", True)),
        comparison_count=user.get("comparison_count", 0),
        profile_image=user.get("profile_image"),
        created_at=user.get("created_at")
    )


def get_current_user_required(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """Get current user from JWT token. Raises 401 if not authenticated."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token_data = decode_token(credentials.credentials)
    
    if not token_data or not token_data.user_id:
        raise credentials_exception
    
    user = user_db.get_user_by_id(token_data.user_id)
    
    if not user:
        raise credentials_exception
    
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name"),
        is_active=bool(user.get("is_active", True)),
        comparison_count=user.get("comparison_count", 0),
        profile_image=user.get("profile_image"),
        created_at=user.get("created_at")
    )
