"""User service for database operations using SQLAlchemy."""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from ..db.base import SessionLocal
from ..db.models import User, Comparison, OTPToken, ResetToken
from ..db.repositories import (
    UserRepository, 
    ComparisonRepository, 
    OTPTokenRepository, 
    ResetTokenRepository
)

logger = logging.getLogger(__name__)


class UserService:
    """
    Service class for user-related database operations.
    Provides a clean interface for user management.
    """
    
    def __init__(self):
        pass
    
    def _get_db(self) -> Session:
        """Get a database session."""
        return SessionLocal()
    
    # ============ User Operations ============
    
    def create_user(self, email: str, password_hash: str, full_name: Optional[str] = None) -> Optional[Dict]:
        """Create a new user."""
        try:
            db = self._get_db()
            try:
                repo = UserRepository(db)
                user = repo.create(email, password_hash, full_name)
                return self._user_to_dict(user)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        try:
            db = self._get_db()
            try:
                repo = UserRepository(db)
                user = repo.get_by_id(user_id)
                return self._user_to_dict(user) if user else None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        try:
            db = self._get_db()
            try:
                repo = UserRepository(db)
                user = repo.get_by_email(email)
                return self._user_to_dict(user) if user else None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def update_user(self, user_id: str, **kwargs) -> Optional[Dict]:
        """Update user fields."""
        try:
            db = self._get_db()
            try:
                repo = UserRepository(db)
                user = repo.get_by_id(user_id)
                if user:
                    user = repo.update(user, **kwargs)
                    return self._user_to_dict(user)
                return None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None
    
    def update_password(self, user_id: str, new_password_hash: str) -> bool:
        """Update user password."""
        try:
            db = self._get_db()
            try:
                repo = UserRepository(db)
                user = repo.get_by_id(user_id)
                if user:
                    repo.update(user, password_hash=new_password_hash)
                    return True
                return False
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False
    
    def increment_comparison_count(self, user_id: str) -> int:
        """Increment user's comparison count."""
        try:
            db = self._get_db()
            try:
                repo = UserRepository(db)
                return repo.increment_comparison_count(user_id)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error incrementing comparison count: {e}")
            return 0
    
    def _user_to_dict(self, user: User) -> Dict:
        """Convert User model to dictionary."""
        if not user:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "comparison_count": user.comparison_count,
            "profile_image": user.profile_image,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "password_hash": user.password_hash  # Include for auth verification
        }
    
    # ============ OTP Operations ============
    
    def store_otp(self, email: str, otp_code: str, user_data: Dict, expiry_minutes: int = 10) -> bool:
        """Store OTP for email verification."""
        try:
            db = self._get_db()
            try:
                repo = OTPTokenRepository(db)
                repo.create(email, otp_code, user_data, expiry_minutes)
                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error storing OTP: {e}")
            return False
    
    def verify_otp(self, email: str, otp_code: str) -> Optional[Dict]:
        """Verify OTP and return user data if valid."""
        try:
            db = self._get_db()
            try:
                repo = OTPTokenRepository(db)
                return repo.verify(email, otp_code)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return None
    
    def delete_otp(self, email: str):
        """Delete OTP for email."""
        try:
            db = self._get_db()
            try:
                repo = OTPTokenRepository(db)
                repo.delete_by_email(email)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error deleting OTP: {e}")
    
    def get_otp_info(self, email: str) -> Optional[Dict]:
        """Get OTP info for resend logic."""
        try:
            db = self._get_db()
            try:
                repo = OTPTokenRepository(db)
                token = repo.get_by_email(email)
                if token and not token.is_expired:
                    return {
                        "exists": True,
                        "user_data": token.user_data
                    }
                return None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting OTP info: {e}")
            return None
    
    # ============ Reset Token Operations ============
    
    def store_reset_token(self, user_id: str, email: str, token: str, expiry_minutes: int = 30) -> bool:
        """Store password reset token."""
        try:
            db = self._get_db()
            try:
                repo = ResetTokenRepository(db)
                repo.create(user_id, email, token, expiry_minutes)
                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error storing reset token: {e}")
            return False
    
    def verify_reset_token(self, email: str, token: str) -> bool:
        """Verify password reset token."""
        try:
            db = self._get_db()
            try:
                repo = ResetTokenRepository(db)
                return repo.verify(email, token)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error verifying reset token: {e}")
            return False
    
    def invalidate_reset_token(self, email: str):
        """Invalidate all reset tokens for email."""
        try:
            db = self._get_db()
            try:
                repo = ResetTokenRepository(db)
                repo.invalidate(email)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error invalidating reset token: {e}")


# Global instance for backward compatibility
user_service = UserService()


# Backward-compatible interface (matches old user_db API)
class UserDB:
    """Backward-compatible wrapper for UserService."""
    
    def create_user(self, email: str, password_hash: str, full_name: Optional[str] = None) -> Optional[Dict]:
        return user_service.create_user(email, password_hash, full_name)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        return user_service.get_user_by_id(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        return user_service.get_user_by_email(email)
    
    def update_profile(self, user_id: str, full_name: Optional[str] = None, profile_image: Optional[str] = None) -> Optional[Dict]:
        kwargs = {}
        if full_name is not None:
            kwargs['full_name'] = full_name
        if profile_image is not None:
            kwargs['profile_image'] = profile_image
        return user_service.update_user(user_id, **kwargs)
    
    def update_password(self, user_id: str, new_password_hash: str) -> bool:
        return user_service.update_password(user_id, new_password_hash)
    
    def increment_comparison_count(self, user_id: str) -> int:
        return user_service.increment_comparison_count(user_id)


# Global instance for backward compatibility
user_db = UserDB()
