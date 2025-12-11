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
        
        # HTML version with Outlook-compatible styling (no CSS gradients)
        html_content = f"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Your verification code: {otp} - Pixel Perfect UI</title>
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, Helvetica, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="500" cellspacing="0" cellpadding="0" border="0" style="max-width: 500px; background-color: #ffffff;">
                    
                    <!-- Header -->
                    <tr>
                        <td align="center" bgcolor="#8b5cf6" style="background-color: #8b5cf6; padding: 32px 40px;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: bold; font-family: Arial, Helvetica, sans-serif;">Pixel Perfect UI</h1>
                            <p style="margin: 8px 0 0 0; color: #e9d5ff; font-size: 14px; font-family: Arial, Helvetica, sans-serif;">Email Verification</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <p style="margin: 0 0 12px 0; color: #374151; font-size: 16px; font-family: Arial, Helvetica, sans-serif;">
                                {greeting}
                            </p>
                            <p style="margin: 0 0 24px 0; color: #6b7280; font-size: 15px; line-height: 24px; font-family: Arial, Helvetica, sans-serif;">
                                Your One-Time Password (OTP) for Pixel Perfect UI is:
                            </p>
                            
                            <!-- OTP Code Box -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0;">
                                <tr>
                                    <td align="center" bgcolor="#f3e8ff" style="background-color: #f3e8ff; border: 1px solid #d8b4fe; padding: 20px;">
                                        <p style="margin: 0 0 6px 0; color: #7c3aed; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; font-family: Arial, Helvetica, sans-serif;">YOUR OTP CODE</p>
                                        <p style="margin: 0; color: #7c3aed; font-size: 32px; font-weight: bold; letter-spacing: 6px; font-family: 'Courier New', Courier, monospace;">{otp}</p>
                                    </td>
                                </tr>
                            </table>
                            
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td align="center" style="padding: 16px 0;">
                                        <p style="margin: 0 0 4px 0; color: #374151; font-size: 14px; font-family: Arial, Helvetica, sans-serif;">
                                            This code will remain valid for <strong>{OTP_EXPIRY_MINUTES} minutes</strong>.
                                        </p>
                                        <p style="margin: 0; color: #6b7280; font-size: 14px; font-family: Arial, Helvetica, sans-serif;">
                                            Please enter it in the app to complete your verification.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top: 24px;">
                                <tr>
                                    <td style="border-top: 1px solid #e5e7eb; padding-top: 20px;">
                                        <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 13px; line-height: 20px; font-family: Arial, Helvetica, sans-serif;">
                                            If you did not request this code, please ignore this email or contact our support team immediately.
                                        </p>
                                        <p style="margin: 0; color: #374151; font-size: 14px; line-height: 21px; font-family: Arial, Helvetica, sans-serif;">
                                            Best regards,<br />
                                            <strong>The Pixel Perfect UI Team</strong>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td align="center" bgcolor="#f9fafb" style="background-color: #f9fafb; padding: 20px 40px; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0; color: #9ca3af; font-size: 11px; font-family: Arial, Helvetica, sans-serif;">
                                &copy; 2025 Pixel Perfect UI. All rights reserved.
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
        
        # HTML version with Outlook-compatible styling (no CSS gradients)
        html_content = f"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Password Reset - Pixel Perfect UI</title>
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: Arial, Helvetica, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f3f4f6;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="520" cellspacing="0" cellpadding="0" border="0" style="max-width: 520px; background-color: #ffffff;">
                    <!-- Header -->
                    <tr>
                        <td align="center" bgcolor="#7c3aed" style="background-color: #7c3aed; padding: 32px 20px;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: bold; font-family: Arial, Helvetica, sans-serif;">Pixel Perfect UI</h1>
                            <p style="margin: 8px 0 0 0; color: #e9d5ff; font-size: 14px; font-family: Arial, Helvetica, sans-serif;">Password Reset Request</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 32px 24px;">
                            <p style="margin: 0 0 16px 0; color: #374151; font-size: 16px; line-height: 24px; font-family: Arial, Helvetica, sans-serif;">
                                {greeting}
                            </p>
                            <p style="margin: 0 0 24px 0; color: #374151; font-size: 16px; line-height: 24px; font-family: Arial, Helvetica, sans-serif;">
                                We received a request to reset your password for your Pixel Perfect UI account.
                                If you made this request, click the button below to reset your password:
                            </p>
                            
                            <!-- Reset Button - Outlook compatible -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 32px 0;">
                                <tr>
                                    <td align="center">
                                        <!--[if mso]>
                                        <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{reset_url}" style="height:50px;v-text-anchor:middle;width:200px;" arcsize="10%" strokecolor="#7c3aed" fillcolor="#7c3aed">
                                        <w:anchorlock/>
                                        <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">Reset Password</center>
                                        </v:roundrect>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                        <a href="{reset_url}" target="_blank" style="display: inline-block; background-color: #7c3aed; color: #ffffff; text-decoration: none; padding: 14px 32px; font-size: 16px; font-weight: bold; font-family: Arial, Helvetica, sans-serif; border-radius: 8px;">Reset Password</a>
                                        <!--<![endif]-->
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Link fallback -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0;">
                                <tr>
                                    <td bgcolor="#f9fafb" style="background-color: #f9fafb; padding: 16px; border-radius: 8px;">
                                        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 12px; font-family: Arial, Helvetica, sans-serif;">Or copy and paste this link into your browser:</p>
                                        <p style="margin: 0; color: #7c3aed; font-size: 12px; word-break: break-all; font-family: Arial, Helvetica, sans-serif;">{reset_url}</p>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px; text-align: center; font-family: Arial, Helvetica, sans-serif;">
                                This link expires in <strong>{RESET_TOKEN_EXPIRY_MINUTES} minutes</strong>
                            </p>
                            
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0;">
                                <tr>
                                    <td style="border-top: 1px solid #e5e7eb; padding-top: 24px;">
                                        <p style="margin: 0 0 16px 0; color: #374151; font-size: 14px; line-height: 21px; font-family: Arial, Helvetica, sans-serif;">
                                            If you did not request a password reset, please ignore this email. Your account will remain secure.
                                        </p>
                                        <p style="margin: 0 0 16px 0; color: #374151; font-size: 14px; line-height: 21px; font-family: Arial, Helvetica, sans-serif;">
                                            If you need any further assistance, feel free to contact our support team.
                                        </p>
                                        <p style="margin: 0; color: #374151; font-size: 14px; line-height: 21px; font-family: Arial, Helvetica, sans-serif;">
                                            Best regards,<br />
                                            <strong>The Pixel Perfect UI Team</strong>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td align="center" bgcolor="#f9fafb" style="background-color: #f9fafb; padding: 24px;">
                            <p style="margin: 0; color: #9ca3af; font-size: 12px; font-family: Arial, Helvetica, sans-serif;">
                                &copy; 2025 Pixel Perfect UI. All rights reserved.
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
