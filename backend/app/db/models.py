"""SQLAlchemy ORM models for Pixel Perfect UI."""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, Enum
)
from sqlalchemy.orm import relationship, declarative_mixin, declared_attr
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from .base import Base


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


@declarative_mixin
class TimestampMixin:
    """Mixin for created_at and updated_at timestamp fields."""
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=func.now(), nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class JobStatus(str, enum.Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base, TimestampMixin):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    comparison_count = Column(Integer, default=0)
    profile_image = Column(Text, nullable=True)

    # Relationships
    comparisons = relationship("Comparison", back_populates="user", cascade="all, delete-orphan")
    otp_tokens = relationship("OTPToken", back_populates="user", cascade="all, delete-orphan")
    reset_tokens = relationship("ResetToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class Comparison(Base, TimestampMixin):
    """Comparison job model."""
    __tablename__ = "comparisons"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    comparison_number = Column(Integer, nullable=True)
    
    # Input data
    figma_url = Column(Text, nullable=True)
    website_url = Column(Text, nullable=False)
    viewport_width = Column(Integer, default=1920)
    viewport_height = Column(Integer, default=1080)
    viewport_name = Column(String(50), default="desktop")
    comparison_mode = Column(String(20), default="single")
    
    # Results
    match_score = Column(Float, default=0.0)
    total_differences = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)
    
    # Report data
    report_json = Column(JSON, nullable=True)
    figma_screenshot_url = Column(Text, nullable=True)
    website_screenshot_url = Column(Text, nullable=True)
    visual_diff_url = Column(Text, nullable=True)
    
    # Metadata
    project_name = Column(String(255), nullable=True)
    tags = Column(JSON, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="comparisons")
    viewport_results = relationship("ViewportResult", back_populates="comparison", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Comparison {self.job_id}>"


class ViewportResult(Base, TimestampMixin):
    """Viewport-specific results for responsive comparisons."""
    __tablename__ = "viewport_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comparison_id = Column(String(36), ForeignKey("comparisons.id"), nullable=False, index=True)
    
    viewport_name = Column(String(50), nullable=False)
    viewport_width = Column(Integer, nullable=False)
    viewport_height = Column(Integer, nullable=False)
    
    match_score = Column(Float, default=0.0)
    total_differences = Column(Integer, default=0)
    
    figma_screenshot_url = Column(Text, nullable=True)
    website_screenshot_url = Column(Text, nullable=True)
    visual_diff_url = Column(Text, nullable=True)
    report_json = Column(JSON, nullable=True)

    # Relationships
    comparison = relationship("Comparison", back_populates="viewport_results")

    def __repr__(self):
        return f"<ViewportResult {self.viewport_name} for {self.comparison_id}>"


class Job(Base, TimestampMixin):
    """Job progress and result storage (replaces Redis)."""
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    status = Column(String(20), default="pending")
    
    # Progress tracking
    progress_percent = Column(Integer, default=0)
    progress_step = Column(String(100), nullable=True)
    progress_message = Column(Text, nullable=True)
    progress_details = Column(JSON, nullable=True)
    
    # Result storage
    result_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Job {self.id} - {self.status}>"


class OTPToken(Base, TimestampMixin):
    """OTP tokens for email verification."""
    __tablename__ = "otp_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=False, index=True)
    otp_code = Column(String(10), nullable=False)
    user_data = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="otp_tokens")

    def __repr__(self):
        return f"<OTPToken {self.email}>"

    @property
    def is_expired(self):
        return datetime.now() > self.expires_at


class ResetToken(Base, TimestampMixin):
    """Password reset tokens."""
    __tablename__ = "reset_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="reset_tokens")

    def __repr__(self):
        return f"<ResetToken {self.email}>"

    @property
    def is_expired(self):
        return datetime.now() > self.expires_at
