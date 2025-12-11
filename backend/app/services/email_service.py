"""Email service for sending OTP verification and password reset emails."""

import os
import random
import string
import smtplib
import logging
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
import json
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Email configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USER)
SENDER_NAME = os.getenv("SENDER_NAME", "Pixel Perfect UI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# OTP Configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10

# Password Reset Configuration
RESET_TOKEN_LENGTH = 32
RESET_TOKEN_EXPIRY_MINUTES = 30

# Import user service for PostgreSQL storage
from .user_service import user_service


class OTPStorage:
    """PostgreSQL-based OTP storage using SQLAlchemy."""
    
    def store_otp(self, email: str, otp: str, user_data: Dict):
        """Store OTP with user data and expiry."""
        user_service.store_otp(email, otp, user_data, OTP_EXPIRY_MINUTES)
    
    def verify_otp(self, email: str, otp: str) -> Optional[Dict]:
        """Verify OTP and return user data if valid."""
        return user_service.verify_otp(email, otp)
    
    def remove_otp(self, email: str):
        """Remove OTP for email."""
        user_service.delete_otp(email)
    
    def get_otp_info(self, email: str) -> Optional[Dict]:
        """Get OTP info (for resend logic) - returns OTP info with user_data."""
        return user_service.get_otp_info(email)


# Global OTP storage instance
otp_storage = OTPStorage()


def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate a random numeric OTP."""
    return ''.join(random.choices(string.digits, k=length))


def send_otp_email(email: str, otp: str, full_name: Optional[str] = None) -> bool:
    """
    Send OTP verification email.
    
    Args:
        email: Recipient email address
        otp: OTP code to send
        full_name: Optional recipient name
        
    Returns:
        True if email sent successfully, False otherwise
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. OTP email not sent.")
        # In development, log the OTP instead
        logger.info(f"[DEV MODE] OTP for {email}: {otp}")
        return True  # Return True in dev mode to allow testing
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your verification code: {otp} - Pixel Perfect UI"
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = email
        
        # Greeting
        greeting = f"Hi {full_name}," if full_name else "Hi there,"
        
        # Plain text version
        text_content = f"""
{greeting}

Your One-Time Password (OTP) for Pixel Perfect UI is:

🔐 {otp}

This code will remain valid for {OTP_EXPIRY_MINUTES} minutes.
Please enter it in the app to complete your verification.

If you did not request this code, please ignore this email or contact our support team immediately.

Best regards,
The Pixel Perfect UI Team
        """
        
        # HTML version with refined professional styling matching the design pattern
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your verification code: {otp} - Pixel Perfect UI</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5; line-height: 1.5;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f5f5f5; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 500px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%); padding: 32px 40px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 600; letter-spacing: 0.5px;">Pixel Perfect UI</h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px; font-weight: 400;">Email Verification</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <div style="text-align: left; margin-bottom: 24px;">
                                <p style="margin: 0 0 12px 0; color: #374151; font-size: 16px; font-weight: 400;">
                                    {greeting}
                                </p>
                                <p style="margin: 0; color: #6b7280; font-size: 15px; line-height: 1.6;">
                                    Your One-Time Password (OTP) for Pixel Perfect UI is:
                                </p>
                            </div>
                            
                            <!-- OTP Code Box -->
                            <div style="background: linear-gradient(135deg, #f3e8ff 0%, #ede9fe 100%); border: 1px solid #d8b4fe; border-radius: 8px; padding: 20px; text-align: center; margin: 24px 0;">
                                <p style="margin: 0 0 6px 0; color: #7c3aed; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">🔐 YOUR OTP CODE</p>
                                <p style="margin: 0; color: #7c3aed; font-size: 28px; font-weight: 700; letter-spacing: 3px; font-family: 'Courier New', monospace;">{otp}</p>
                            </div>
                            
                            <div style="text-align: center; margin: 24px 0;">
                                <p style="margin: 0 0 4px 0; color: #374151; font-size: 14px; line-height: 1.5;">
                                    This code will remain valid for <strong>{OTP_EXPIRY_MINUTES} minutes</strong>.
                                </p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.5;">
                                    Please enter it in the app to complete your verification.
                                </p>
                            </div>
                            
                            <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 28px;">
                                <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 13px; line-height: 1.5;">
                                    If you did not request this code, please ignore this email or contact our support team immediately.
                                </p>
                                
                                <p style="margin: 0; color: #374151; font-size: 14px; line-height: 1.5;">
                                    Best regards,<br>
                                    <strong>The Pixel Perfect UI Team</strong>
                                </p>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f9fafb; padding: 20px 40px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0; color: #9ca3af; font-size: 11px; line-height: 1.4;">
                                © 2025 Pixel Perfect UI. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        # Attach both versions
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
        
        logger.info(f"OTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False


def send_verification_otp(email: str, password: str, full_name: Optional[str] = None) -> Dict:
    """
    Generate OTP, store user data, and send verification email.
    
    Args:
        email: User email
        password: User password (will be stored temporarily)
        full_name: Optional user name
        
    Returns:
        Dict with success status and message
    """
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP with user data
    user_data = {
        "email": email,
        "password": password,
        "full_name": full_name
    }
    otp_storage.store_otp(email, otp, user_data)
    
    # Send email
    email_sent = send_otp_email(email, otp, full_name)
    
    if email_sent:
        return {
            "success": True,
            "message": f"Verification code sent to {email}",
            "expires_in_minutes": OTP_EXPIRY_MINUTES
        }
    else:
        # Remove stored OTP if email failed
        otp_storage.remove_otp(email)
        return {
            "success": False,
            "message": "Failed to send verification email. Please try again."
        }


def verify_and_get_user_data(email: str, otp: str) -> Optional[Dict]:
    """
    Verify OTP and return user data for registration.
    
    Args:
        email: User email
        otp: OTP code to verify
        
    Returns:
        User data dict if valid, None otherwise
    """
    return otp_storage.verify_otp(email, otp)


def resend_otp(email: str) -> Dict:
    """
    Resend OTP for an existing pending verification.
    
    Args:
        email: User email
        
    Returns:
        Dict with success status and message
    """
    existing = otp_storage.get_otp_info(email)
    
    if not existing:
        return {
            "success": False,
            "message": "No pending verification found. Please sign up again."
        }
    
    # Generate new OTP
    otp = generate_otp()
    user_data = existing["user_data"]
    
    # Update storage with new OTP
    otp_storage.store_otp(email, otp, user_data)
    
    # Send email
    email_sent = send_otp_email(email, otp, user_data.get("full_name"))
    
    if email_sent:
        return {
            "success": True,
            "message": f"New verification code sent to {email}",
            "expires_in_minutes": OTP_EXPIRY_MINUTES
        }
    else:
        return {
            "success": False,
            "message": "Failed to send verification email. Please try again."
        }


# ============================================================================
# Password Reset Functions
# ============================================================================


class ResetTokenStorage:
    """PostgreSQL-based reset token storage using SQLAlchemy."""
    
    def store_token(self, email: str, token: str, user_id: str = None):
        """Store reset token with expiry."""
        if user_id:
            user_service.store_reset_token(user_id, email, token, RESET_TOKEN_EXPIRY_MINUTES)
    
    def verify_token(self, email: str, token: str) -> bool:
        """Verify reset token. Returns True if valid."""
        return user_service.verify_reset_token(email, token)
    
    def remove_token(self, email: str):
        """Remove reset token for email."""
        user_service.invalidate_reset_token(email)


# Global reset token storage instance
reset_token_storage = ResetTokenStorage()


def generate_reset_token() -> str:
    """Generate a secure random reset token."""
    return secrets.token_urlsafe(RESET_TOKEN_LENGTH)


def send_password_reset_email(email: str, token: str, full_name: Optional[str] = None) -> bool:
    """
    Send password reset email with reset link.
    
    Args:
        email: Recipient email address
        token: Reset token
        full_name: Optional recipient name
        
    Returns:
        True if email sent successfully, False otherwise
    """
    # Build reset URL
    reset_params = urlencode({"email": email, "token": token})
    reset_url = f"{FRONTEND_URL}/reset-password?{reset_params}"
    
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Password reset email not sent.")
        # In development, log the reset link instead
        logger.info(f"[DEV MODE] Password reset link for {email}: {reset_url}")
        return True  # Return True in dev mode to allow testing
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset Your Password - Pixel Perfect UI"
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = email
        
        # Greeting
        greeting = f"Hi {full_name}," if full_name else "Hi there,"
        
        # Plain text version
        text_content = f"""
{greeting}

We received a request to reset your password for your Pixel Perfect UI account.

If you made this request, click the link below to reset your password:

{reset_url}

This link will expire in {RESET_TOKEN_EXPIRY_MINUTES} minutes.

If you did not request a password reset, please ignore this email.
Your account will remain secure.

If you need any further assistance, feel free to contact our support team.

Best regards,
The Pixel Perfect UI Team
        """
        
        # HTML version with styling
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f3f4f6; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 520px; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #7c3aed 0%, #a855f7 50%, #6366f1 100%); padding: 32px; border-radius: 16px 16px 0 0; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">Pixel Perfect UI</h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.8); font-size: 14px;">Password Reset Request</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 32px;">
                            <p style="margin: 0 0 16px 0; color: #374151; font-size: 16px; line-height: 1.6;">
                                {greeting}
                            </p>
                            <p style="margin: 0 0 24px 0; color: #374151; font-size: 16px; line-height: 1.6;">
                                We received a request to reset your password for your Pixel Perfect UI account.
                                If you made this request, click the button below to reset your password:
                            </p>
                            
                            <!-- Reset Button -->
                            <div style="text-align: center; margin: 32px 0;">
                                <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%); color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 12px; font-size: 16px; font-weight: 600; box-shadow: 0 4px 14px rgba(124, 58, 237, 0.4);">
                                    👉 Reset Password
                                </a>
                            </div>
                            
                            <!-- Link fallback -->
                            <div style="background-color: #f9fafb; border-radius: 8px; padding: 16px; margin: 24px 0;">
                                <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 12px;">Or copy and paste this link into your browser:</p>
                                <p style="margin: 0; color: #7c3aed; font-size: 12px; word-break: break-all;">{reset_url}</p>
                            </div>
                            
                            <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px; text-align: center;">
                                ⏱️ This link expires in <strong>{RESET_TOKEN_EXPIRY_MINUTES} minutes</strong>
                            </p>
                            
                            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
                            
                            <p style="margin: 0 0 16px 0; color: #374151; font-size: 14px; line-height: 1.6;">
                                If you did not request a password reset, please ignore this email. Your account will remain secure.
                            </p>
                            
                            <p style="margin: 0; color: #374151; font-size: 14px; line-height: 1.6;">
                                If you need any further assistance, feel free to contact our support team.
                            </p>
                            
                            <p style="margin: 24px 0 0 0; color: #374151; font-size: 14px; line-height: 1.6;">
                                Best regards,<br>
                                <strong>The Pixel Perfect UI Team</strong>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f9fafb; padding: 24px; border-radius: 0 0 16px 16px; text-align: center;">
                            <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                © 2025 Pixel Perfect UI. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        # Attach both versions
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
        
        logger.info(f"Password reset email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        return False


def send_password_reset_request(email: str, full_name: Optional[str] = None, user_id: Optional[str] = None) -> Dict:
    """
    Generate reset token and send password reset email.
    
    Args:
        email: User email
        full_name: Optional user name
        user_id: User ID for storing token
        
    Returns:
        Dict with success status and message
    """
    # Generate token
    token = generate_reset_token()
    
    # Store token (requires user_id for PostgreSQL storage)
    if user_id:
        reset_token_storage.store_token(email, token, user_id)
    
    # Send email
    email_sent = send_password_reset_email(email, token, full_name)
    
    if email_sent:
        return {
            "success": True,
            "message": f"Password reset instructions sent to {email}",
            "expires_in_minutes": RESET_TOKEN_EXPIRY_MINUTES
        }
    else:
        # Remove stored token if email failed
        reset_token_storage.remove_token(email)
        return {
            "success": False,
            "message": "Failed to send password reset email. Please try again."
        }


def verify_reset_token(email: str, token: str) -> bool:
    """
    Verify password reset token.
    
    Args:
        email: User email
        token: Reset token
        
    Returns:
        True if token is valid, False otherwise
    """
    return reset_token_storage.verify_token(email, token)


def invalidate_reset_token(email: str):
    """
    Invalidate (remove) reset token after successful password reset.
    
    Args:
        email: User email
    """
    reset_token_storage.remove_token(email)
