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
    OTPResponse
)
from ..services.auth import (
    register_user,
    authenticate_user,
    create_access_token,
    get_current_user_required,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..services.email_service import (
    send_verification_otp,
    verify_and_get_user_data,
    resend_otp
)
from ..models.database import user_db

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
