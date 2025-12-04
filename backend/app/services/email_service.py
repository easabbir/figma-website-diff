"""Email service for sending OTP verification emails."""

import os
import random
import string
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Email configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USER)
SENDER_NAME = os.getenv("SENDER_NAME", "UI Diff Checker")

# OTP Configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10

# File-based OTP storage (use Redis in production)
OTP_STORAGE_FILE = Path(__file__).parent.parent.parent / "data" / "otp_storage.json"


class OTPStorage:
    """Simple file-based OTP storage. Use Redis in production."""
    
    def __init__(self):
        self.storage_file = OTP_STORAGE_FILE
        self._ensure_storage_file()
    
    def _ensure_storage_file(self):
        """Ensure storage file exists."""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_file.exists():
            self.storage_file.write_text("{}")
    
    def _load(self) -> Dict:
        """Load OTP data from file."""
        try:
            return json.loads(self.storage_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save(self, data: Dict):
        """Save OTP data to file."""
        self.storage_file.write_text(json.dumps(data, indent=2))
    
    def store_otp(self, email: str, otp: str, user_data: Dict):
        """Store OTP with user data and expiry."""
        data = self._load()
        data[email.lower()] = {
            "otp": otp,
            "user_data": user_data,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
        }
        self._save(data)
    
    def verify_otp(self, email: str, otp: str) -> Optional[Dict]:
        """Verify OTP and return user data if valid."""
        data = self._load()
        email_lower = email.lower()
        
        if email_lower not in data:
            return None
        
        stored = data[email_lower]
        expires_at = datetime.fromisoformat(stored["expires_at"])
        
        # Check expiry
        if datetime.utcnow() > expires_at:
            # OTP expired, remove it
            del data[email_lower]
            self._save(data)
            return None
        
        # Check OTP match
        if stored["otp"] != otp:
            return None
        
        # Valid OTP - get user data and remove from storage
        user_data = stored["user_data"]
        del data[email_lower]
        self._save(data)
        
        return user_data
    
    def remove_otp(self, email: str):
        """Remove OTP for email."""
        data = self._load()
        email_lower = email.lower()
        if email_lower in data:
            del data[email_lower]
            self._save(data)
    
    def get_otp_info(self, email: str) -> Optional[Dict]:
        """Get OTP info without verifying (for resend logic)."""
        data = self._load()
        return data.get(email.lower())


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
        msg["Subject"] = f"Your verification code: {otp}"
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = email
        
        # Greeting
        greeting = f"Hi {full_name}," if full_name else "Hi there,"
        
        # Plain text version
        text_content = f"""
{greeting}

Your verification code is: {otp}

This code will expire in {OTP_EXPIRY_MINUTES} minutes.

If you didn't request this code, please ignore this email.

Best regards,
The UI Diff Checker Team
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
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 480px; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #7c3aed 0%, #a855f7 50%, #6366f1 100%); padding: 32px; border-radius: 16px 16px 0 0; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">UI Diff Checker</h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.8); font-size: 14px;">Email Verification</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 32px;">
                            <p style="margin: 0 0 16px 0; color: #374151; font-size: 16px; line-height: 1.5;">
                                {greeting}
                            </p>
                            <p style="margin: 0 0 24px 0; color: #374151; font-size: 16px; line-height: 1.5;">
                                Use the verification code below to complete your signup:
                            </p>
                            
                            <!-- OTP Code -->
                            <div style="background: linear-gradient(135deg, #f3e8ff 0%, #ede9fe 100%); border: 2px solid #c4b5fd; border-radius: 12px; padding: 24px; text-align: center; margin: 0 0 24px 0;">
                                <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Verification Code</p>
                                <p style="margin: 0; color: #7c3aed; font-size: 36px; font-weight: 700; letter-spacing: 8px; font-family: monospace;">{otp}</p>
                            </div>
                            
                            <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px; text-align: center;">
                                ⏱️ This code expires in <strong>{OTP_EXPIRY_MINUTES} minutes</strong>
                            </p>
                            
                            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
                            
                            <p style="margin: 0; color: #9ca3af; font-size: 13px; line-height: 1.5;">
                                If you didn't request this code, you can safely ignore this email. Someone might have entered your email by mistake.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f9fafb; padding: 24px; border-radius: 0 0 16px 16px; text-align: center;">
                            <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                © 2025 UI Diff Checker. All rights reserved.
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
