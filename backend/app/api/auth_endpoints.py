"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta

from ..models.user import (
    UserCreate, 
    UserLogin, 
    UserResponse, 
    Token,
    OTPRequest,
    OTPVerify,
    OTPResend,
    OTPResponse,
    PasswordChange,
    ProfileUpdate,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from ..services.auth import (
    register_user,
    authenticate_user,
    create_access_token,
    get_current_user_required,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    verify_password,
    get_password_hash
)
from ..services.email_service import (
    send_verification_otp,
    verify_and_get_user_data,
    resend_otp,
    send_password_reset_request,
    verify_reset_token,
    invalidate_reset_token
)
from ..services.user_service import user_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup/request-otp", response_model=OTPResponse)
async def request_signup_otp(user_data: OTPRequest):
    """
    Step 1: Request OTP for signup.
    Sends verification code to email.
    
    Args:
        user_data: User registration data (email, password, full_name)
        
    Returns:
        OTP response with success status
    """
    # Check if email already exists
    existing_user = user_db.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Send OTP
    result = send_verification_otp(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return OTPResponse(
        success=True,
        message=result["message"],
        expires_in_minutes=result.get("expires_in_minutes")
    )


@router.post("/signup/verify-otp", response_model=Token)
async def verify_signup_otp(otp_data: OTPVerify):
    """
    Step 2: Verify OTP and complete signup.
    Creates user account if OTP is valid.
    
    Args:
        otp_data: Email and OTP code
        
    Returns:
        JWT access token on success
    """
    # Verify OTP and get user data
    user_data = verify_and_get_user_data(otp_data.email, otp_data.otp)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Create user account
    user_create = UserCreate(
        email=user_data["email"],
        password=user_data["password"],
        full_name=user_data.get("full_name")
    )
    
    user = register_user(user_create)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create account. Email may already be registered."
        )
    
    # Create access token and log user in
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/signup/resend-otp", response_model=OTPResponse)
async def resend_signup_otp(resend_data: OTPResend):
    """
    Resend OTP for pending signup.
    
    Args:
        resend_data: Email address
        
    Returns:
        OTP response with success status
    """
    result = resend_otp(resend_data.email)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return OTPResponse(
        success=True,
        message=result["message"],
        expires_in_minutes=result.get("expires_in_minutes")
    )


# Keep legacy signup endpoint for backwards compatibility (but it won't work without OTP)
@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED, deprecated=True)
async def signup(user_data: UserCreate):
    """
    [DEPRECATED] Direct signup without OTP verification.
    Use /signup/request-otp and /signup/verify-otp instead.
    """
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Direct signup is disabled. Please use OTP verification."
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Login with email and password.
    
    Args:
        credentials: Login credentials (email, password)
        
    Returns:
        JWT access token
    """
    user = authenticate_user(credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user_required)):
    """
    Get current authenticated user info.
    
    Returns:
        Current user data
    """
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: UserResponse = Depends(get_current_user_required)
):
    """
    Update user profile (name, profile image).
    
    Args:
        profile_data: Profile update data
        current_user: Current authenticated user
        
    Returns:
        Updated user data
    """
    update_fields = {}
    
    if profile_data.full_name is not None:
        update_fields['full_name'] = profile_data.full_name
    
    if profile_data.profile_image is not None:
        update_fields['profile_image'] = profile_data.profile_image
    
    if update_fields:
        user_db.update_user(current_user.id, **update_fields)
    
    # Fetch updated user
    updated_user = user_db.get_user_by_id(current_user.id)
    
    return UserResponse(
        id=updated_user["id"],
        email=updated_user["email"],
        full_name=updated_user.get("full_name"),
        is_active=bool(updated_user.get("is_active", True)),
        comparison_count=updated_user.get("comparison_count", 0),
        profile_image=updated_user.get("profile_image"),
        created_at=updated_user.get("created_at")
    )


@router.put("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: UserResponse = Depends(get_current_user_required)
):
    """
    Change user password.
    
    Args:
        password_data: Current and new password
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    # Get user with password hash
    user = user_db.get_user_by_id(current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash new password and update
    new_password_hash = get_password_hash(password_data.new_password)
    user_db.update_password(current_user.id, new_password_hash)
    
    return {"message": "Password changed successfully"}


# ============================================================================
# Forgot Password Endpoints
# ============================================================================

@router.post("/forgot-password", response_model=OTPResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request a password reset email.
    
    Sends a password reset link to the user's email if the account exists.
    For security, always returns success even if email doesn't exist.
    
    Args:
        request: Email address for password reset
        
    Returns:
        Success response (always, for security)
    """
    # Check if user exists
    user = user_db.get_user_by_email(request.email)
    
    if user:
        # User exists, send reset email
        result = send_password_reset_request(
            email=request.email,
            full_name=user.get("full_name"),
            user_id=user.get("id")
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    
    # Always return success for security (don't reveal if email exists)
    return OTPResponse(
        success=True,
        message="If an account with this email exists, you will receive a password reset link shortly.",
        expires_in_minutes=30
    )


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using the token from email.
    
    Args:
        request: Email, token, and new password
        
    Returns:
        Success message
    """
    # Verify token
    if not verify_reset_token(request.email, request.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token. Please request a new password reset."
        )
    
    # Get user
    user = user_db.get_user_by_email(request.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash new password and update
    new_password_hash = get_password_hash(request.new_password)
    user_db.update_password(user["id"], new_password_hash)
    
    # Invalidate the reset token
    invalidate_reset_token(request.email)
    
    return {"message": "Password reset successfully. You can now login with your new password."}


@router.post("/verify-reset-token")
async def verify_password_reset_token(request: ResetPasswordRequest):
    """
    Verify if a password reset token is valid (without resetting).
    Used by frontend to check token before showing reset form.
    
    Args:
        request: Email and token (new_password is ignored)
        
    Returns:
        Valid status
    """
    is_valid = verify_reset_token(request.email, request.token)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {"valid": True, "message": "Token is valid"}
