"""PostgreSQL-based job storage for comparison results and progress."""

import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from ..models.schemas import DiffReport, ProgressUpdate
from ..db.base import SessionLocal
from ..db.models import Job

logger = logging.getLogger(__name__)

# Job expiry time
JOB_EXPIRY_HOURS = 24


class JobStorage:
    """
    PostgreSQL-based storage for job results and progress.
    Uses SQLAlchemy for database operations.
    """
    
    def __init__(self):
        self._in_memory_progress: Dict[str, dict] = {}  # Fast in-memory cache for progress
        self._in_memory_results: Dict[str, dict] = {}   # Fast in-memory cache for results
        logger.info("JobStorage initialized with PostgreSQL backend")
    
    def _get_db(self):
        """Get a database session."""
        return SessionLocal()
    
    # ============ Progress Storage ============
    
    def set_progress(self, job_id: str, progress: ProgressUpdate):
        """Store job progress."""
        data = progress.model_dump(mode='json')
        
        # Always update in-memory cache for fast access
        self._in_memory_progress[job_id] = data
        
        # Also persist to database
        try:
            db = self._get_db()
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    job = Job(
                        id=job_id,
                        expires_at=datetime.now() + timedelta(hours=JOB_EXPIRY_HOURS)
                    )
                    db.add(job)
                
                job.progress_percent = data.get('percent', 0)
                job.progress_step = data.get('step')
                job.progress_message = data.get('message')
                job.progress_details = data.get('details')
                job.status = "running" if data.get('percent', 0) < 100 else "completed"
                job.updated_at = datetime.now()
                
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database error storing progress: {e}")
    
    def get_progress(self, job_id: str) -> Optional[ProgressUpdate]:
        """Get job progress."""
        # First check in-memory cache
        data = self._in_memory_progress.get(job_id)
        
        if data is None:
            # Fall back to database
            try:
                db = self._get_db()
                try:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job:
                        data = {
                            "percent": job.progress_percent or 0,
                            "step": job.progress_step,
                            "message": job.progress_message,
                            "details": job.progress_details,
                            "status": job.status
                        }
                        # Cache it
                        self._in_memory_progress[job_id] = data
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Database error getting progress: {e}")
        
        if data:
            return ProgressUpdate(**data)
        return None
    
    def update_progress(self, job_id: str, **kwargs):
        """Update specific fields of job progress."""
        progress = self.get_progress(job_id)
        if progress:
            for key, value in kwargs.items():
                if hasattr(progress, key):
                    setattr(progress, key, value)
            self.set_progress(job_id, progress)
        else:
            # Create new progress
            new_progress = ProgressUpdate(**kwargs)
            self.set_progress(job_id, new_progress)
    
    # ============ Result Storage ============
    
    def set_result(self, job_id: str, report: DiffReport):
        """Store job result."""
        data = report.model_dump(mode='json')
        
        # Update in-memory cache
        self._in_memory_results[job_id] = data
        
        # Persist to database
        try:
            db = self._get_db()
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    job = Job(
                        id=job_id,
                        expires_at=datetime.now() + timedelta(hours=JOB_EXPIRY_HOURS)
                    )
                    db.add(job)
                
                job.result_json = data
                job.status = "completed"
                job.progress_percent = 100
                job.updated_at = datetime.now()
                
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database error storing result: {e}")
    
    def get_result(self, job_id: str) -> Optional[DiffReport]:
        """Get job result."""
        # First check in-memory cache
        data = self._in_memory_results.get(job_id)
        
        if data is None:
            # Fall back to database
            try:
                db = self._get_db()
                try:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job and job.result_json:
                        data = job.result_json
                        # Cache it
                        self._in_memory_results[job_id] = data
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Database error getting result: {e}")
        
        if data:
            # Handle datetime parsing
            if 'created_at' in data and isinstance(data['created_at'], str):
                try:
                    data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                except:
                    pass
            if 'completed_at' in data and isinstance(data['completed_at'], str):
                try:
                    data['completed_at'] = datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00'))
                except:
                    pass
            return DiffReport(**data)
        return None
    
    def has_result(self, job_id: str) -> bool:
        """Check if job result exists."""
        if job_id in self._in_memory_results:
            return True
        
        try:
            db = self._get_db()
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                return job is not None and job.result_json is not None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database error checking result: {e}")
        
        return False
    
    def delete_job(self, job_id: str):
        """Delete job data."""
        # Remove from in-memory cache
        self._in_memory_progress.pop(job_id, None)
        self._in_memory_results.pop(job_id, None)
        
        # Remove from database
        try:
            db = self._get_db()
            try:
                db.query(Job).filter(Job.id == job_id).delete()
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database error deleting job: {e}")
    
    # ============ Utility Methods ============
    
    def list_jobs(self, pattern: str = "*") -> list:
        """List all job IDs."""
        jobs = set()
        
        try:
            db = self._get_db()
            try:
                db_jobs = db.query(Job.id).all()
                jobs.update([j[0] for j in db_jobs])
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database error listing jobs: {e}")
        
        # Add in-memory jobs
        jobs.update(self._in_memory_results.keys())
        
        return list(jobs)
    
    def get_stats(self) -> dict:
        """Get storage statistics."""
        stats = {
            "storage_type": "postgresql",
            "in_memory_results_count": len(self._in_memory_results),
            "in_memory_progress_count": len(self._in_memory_progress),
        }
        
        try:
            db = self._get_db()
            try:
                stats["db_jobs_count"] = db.query(Job).count()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database error getting stats: {e}")
            stats["db_jobs_count"] = 0
        
        return stats
    
    def cleanup_expired(self) -> int:
        """Delete expired jobs. Returns count of deleted jobs."""
        try:
            db = self._get_db()
            try:
                expired = db.query(Job).filter(Job.expires_at < datetime.now()).all()
                count = len(expired)
                for job in expired:
                    self._in_memory_progress.pop(job.id, None)
                    self._in_memory_results.pop(job.id, None)
                    db.delete(job)
                db.commit()
                return count
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database error cleaning up expired jobs: {e}")
            return 0


# Global instance
job_storage = JobStorage()
