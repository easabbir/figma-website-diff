"""User schemas for authentication."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response (no password)."""
    id: str
    is_active: bool = True
    comparison_count: int = 0
    profile_image: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=6)


class ProfileUpdate(BaseModel):
    """Schema for profile update."""
    full_name: Optional[str] = None
    profile_image: Optional[str] = None  # Base64 encoded image or URL


class TokenData(BaseModel):
    """Data encoded in JWT token."""
    user_id: Optional[str] = None
    email: Optional[str] = None


# OTP Verification Schemas
class OTPRequest(BaseModel):
    """Schema for requesting OTP (signup step 1)."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class OTPVerify(BaseModel):
    """Schema for verifying OTP (signup step 2)."""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class OTPResend(BaseModel):
    """Schema for resending OTP."""
    email: EmailStr


class OTPResponse(BaseModel):
    """Response for OTP operations."""
    success: bool
    message: str
    expires_in_minutes: Optional[int] = None
