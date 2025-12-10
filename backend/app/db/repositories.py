"""Repository classes for database operations using SQLAlchemy."""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import logging

from .models import User, Comparison, ViewportResult, Job, OTPToken, ResetToken

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, email: str, password_hash: str, full_name: Optional[str] = None) -> User:
        """Create a new user."""
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email.lower()).first()

    def update(self, user: User, **kwargs) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(user)
        return user

    def increment_comparison_count(self, user_id: str) -> int:
        """Increment user's comparison count and return new count."""
        user = self.get_by_id(user_id)
        if user:
            user.comparison_count += 1
            self.db.commit()
            return user.comparison_count
        return 0

    def delete(self, user: User):
        """Delete a user."""
        self.db.delete(user)
        self.db.commit()


class ComparisonRepository:
    """Repository for Comparison operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, job_id: str, website_url: str, user_id: Optional[str] = None, **kwargs) -> Comparison:
        """Create a new comparison."""
        comparison = Comparison(
            job_id=job_id,
            website_url=website_url,
            user_id=user_id,
            **kwargs
        )
        self.db.add(comparison)
        self.db.commit()
        self.db.refresh(comparison)
        return comparison

    def get_by_id(self, comparison_id: str) -> Optional[Comparison]:
        """Get comparison by ID."""
        return self.db.query(Comparison).filter(Comparison.id == comparison_id).first()

    def get_by_job_id(self, job_id: str) -> Optional[Comparison]:
        """Get comparison by job ID."""
        return self.db.query(Comparison).filter(Comparison.job_id == job_id).first()

    def get_user_comparisons(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Comparison]:
        """Get comparisons for a user."""
        return (
            self.db.query(Comparison)
            .filter(Comparison.user_id == user_id)
            .order_by(desc(Comparison.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_user_comparison_count(self, user_id: str) -> int:
        """Get total comparison count for a user."""
        return self.db.query(Comparison).filter(Comparison.user_id == user_id).count()

    def update(self, comparison: Comparison, **kwargs) -> Comparison:
        """Update comparison fields."""
        for key, value in kwargs.items():
            if hasattr(comparison, key):
                setattr(comparison, key, value)
        self.db.commit()
        self.db.refresh(comparison)
        return comparison

    def update_results(self, job_id: str, **kwargs) -> Optional[Comparison]:
        """Update comparison results by job ID."""
        comparison = self.get_by_job_id(job_id)
        if comparison:
            return self.update(comparison, **kwargs)
        return None

    def delete(self, comparison: Comparison):
        """Delete a comparison."""
        self.db.delete(comparison)
        self.db.commit()

    def delete_by_job_id(self, job_id: str) -> bool:
        """Delete comparison by job ID."""
        comparison = self.get_by_job_id(job_id)
        if comparison:
            self.delete(comparison)
            return True
        return False


class ViewportResultRepository:
    """Repository for ViewportResult operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, comparison_id: str, viewport_name: str, viewport_width: int, viewport_height: int, **kwargs) -> ViewportResult:
        """Create a new viewport result."""
        result = ViewportResult(
            comparison_id=comparison_id,
            viewport_name=viewport_name,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            **kwargs
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_by_comparison(self, comparison_id: str) -> List[ViewportResult]:
        """Get all viewport results for a comparison."""
        return self.db.query(ViewportResult).filter(ViewportResult.comparison_id == comparison_id).all()


class JobRepository:
    """Repository for Job progress and results (replaces Redis)."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, job_id: str, expires_hours: int = 24) -> Job:
        """Create a new job."""
        job = Job(
            id=job_id,
            status="pending",
            expires_at=datetime.now() + timedelta(hours=expires_hours)
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self.db.query(Job).filter(Job.id == job_id).first()

    def get_or_create(self, job_id: str) -> Job:
        """Get existing job or create new one."""
        job = self.get(job_id)
        if not job:
            job = self.create(job_id)
        return job

    def update_progress(self, job_id: str, percent: int, step: str = None, message: str = None, details: Dict = None) -> Optional[Job]:
        """Update job progress."""
        job = self.get_or_create(job_id)
        job.progress_percent = percent
        job.progress_step = step
        job.progress_message = message
        job.progress_details = details
        job.status = "running" if percent < 100 else "completed"
        job.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(job)
        return job

    def set_result(self, job_id: str, result: Dict) -> Optional[Job]:
        """Set job result."""
        job = self.get_or_create(job_id)
        job.result_json = result
        job.status = "completed"
        job.progress_percent = 100
        job.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(job)
        return job

    def set_error(self, job_id: str, error_message: str) -> Optional[Job]:
        """Set job error."""
        job = self.get_or_create(job_id)
        job.error_message = error_message
        job.status = "failed"
        job.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_progress(self, job_id: str) -> Optional[Dict]:
        """Get job progress as dictionary."""
        job = self.get(job_id)
        if not job:
            return None
        return {
            "percent": job.progress_percent,
            "step": job.progress_step,
            "message": job.progress_message,
            "details": job.progress_details,
            "status": job.status
        }

    def get_result(self, job_id: str) -> Optional[Dict]:
        """Get job result."""
        job = self.get(job_id)
        if job and job.result_json:
            return job.result_json
        return None

    def delete(self, job_id: str) -> bool:
        """Delete a job."""
        job = self.get(job_id)
        if job:
            self.db.delete(job)
            self.db.commit()
            return True
        return False

    def cleanup_expired(self) -> int:
        """Delete expired jobs. Returns count of deleted jobs."""
        expired = self.db.query(Job).filter(Job.expires_at < datetime.now()).all()
        count = len(expired)
        for job in expired:
            self.db.delete(job)
        self.db.commit()
        return count

    def list_jobs(self, limit: int = 100) -> List[Dict]:
        """List recent jobs."""
        jobs = self.db.query(Job).order_by(desc(Job.created_at)).limit(limit).all()
        return [
            {
                "job_id": job.id,
                "status": job.status,
                "progress": job.progress_percent,
                "created_at": job.created_at.isoformat() if job.created_at else None
            }
            for job in jobs
        ]


class OTPTokenRepository:
    """Repository for OTP token operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, email: str, otp_code: str, user_data: Dict = None, expiry_minutes: int = 10) -> OTPToken:
        """Create a new OTP token."""
        # Delete any existing OTP for this email
        self.delete_by_email(email)
        
        token = OTPToken(
            email=email.lower(),
            otp_code=otp_code,
            user_data=user_data,
            expires_at=datetime.now() + timedelta(minutes=expiry_minutes)
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_by_email(self, email: str) -> Optional[OTPToken]:
        """Get OTP token by email."""
        return (
            self.db.query(OTPToken)
            .filter(OTPToken.email == email.lower(), OTPToken.used == False)
            .order_by(desc(OTPToken.created_at))
            .first()
        )

    def verify(self, email: str, otp_code: str) -> Optional[Dict]:
        """Verify OTP and return user data if valid."""
        token = self.get_by_email(email)
        if not token:
            return None
        
        if token.is_expired:
            self.db.delete(token)
            self.db.commit()
            return None
        
        if token.otp_code != otp_code:
            return None
        
        # Mark as used and return user data
        user_data = token.user_data
        token.used = True
        self.db.commit()
        
        return user_data

    def delete_by_email(self, email: str):
        """Delete all OTP tokens for an email."""
        self.db.query(OTPToken).filter(OTPToken.email == email.lower()).delete()
        self.db.commit()


class ResetTokenRepository:
    """Repository for password reset token operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, email: str, token: str, expiry_minutes: int = 30) -> ResetToken:
        """Create a new reset token."""
        # Delete any existing tokens for this email
        self.delete_by_email(email)
        
        reset_token = ResetToken(
            user_id=user_id,
            email=email.lower(),
            token=token,
            expires_at=datetime.now() + timedelta(minutes=expiry_minutes)
        )
        self.db.add(reset_token)
        self.db.commit()
        self.db.refresh(reset_token)
        return reset_token

    def get_by_token(self, token: str) -> Optional[ResetToken]:
        """Get reset token by token string."""
        return (
            self.db.query(ResetToken)
            .filter(ResetToken.token == token, ResetToken.used == False)
            .first()
        )

    def verify(self, email: str, token: str) -> bool:
        """Verify reset token."""
        reset_token = self.get_by_token(token)
        if not reset_token:
            return False
        
        if reset_token.email.lower() != email.lower():
            return False
        
        if reset_token.is_expired:
            self.db.delete(reset_token)
            self.db.commit()
            return False
        
        return True

    def invalidate(self, email: str):
        """Invalidate all reset tokens for an email."""
        tokens = self.db.query(ResetToken).filter(ResetToken.email == email.lower()).all()
        for token in tokens:
            token.used = True
        self.db.commit()

    def delete_by_email(self, email: str):
        """Delete all reset tokens for an email."""
        self.db.query(ResetToken).filter(ResetToken.email == email.lower()).delete()
        self.db.commit()
