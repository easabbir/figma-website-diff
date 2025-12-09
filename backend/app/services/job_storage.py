"""Redis-based job storage for comparison results and progress."""

import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime
import os

import redis
from redis.exceptions import ConnectionError as RedisConnectionError

from ..models.schemas import DiffReport, ProgressUpdate

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JOB_EXPIRY_SECONDS = 60 * 60 * 24  # 24 hours


class JobStorage:
    """
    Redis-based storage for job results and progress.
    Falls back to in-memory storage if Redis is unavailable.
    """
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._fallback_results: Dict[str, dict] = {}
        self._fallback_progress: Dict[str, dict] = {}
        self._use_redis = True
        self._connect()
    
    def _connect(self):
        """Attempt to connect to Redis."""
        try:
            self._redis_client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self._redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_URL}")
            self._use_redis = True
        except (RedisConnectionError, Exception) as e:
            logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
            self._redis_client = None
            self._use_redis = False
    
    def _ensure_connection(self) -> bool:
        """Ensure Redis connection is active."""
        if not self._use_redis:
            return False
        try:
            if self._redis_client:
                self._redis_client.ping()
                return True
        except:
            self._use_redis = False
            logger.warning("Redis connection lost, switching to in-memory fallback")
        return False
    
    # ============ Progress Storage ============
    
    def set_progress(self, job_id: str, progress: ProgressUpdate):
        """Store job progress."""
        data = progress.model_dump(mode='json')
        
        if self._ensure_connection():
            try:
                key = f"progress:{job_id}"
                self._redis_client.setex(key, JOB_EXPIRY_SECONDS, json.dumps(data))
                return
            except Exception as e:
                logger.error(f"Redis error storing progress: {e}")
        
        # Fallback to in-memory
        self._fallback_progress[job_id] = data
    
    def get_progress(self, job_id: str) -> Optional[ProgressUpdate]:
        """Get job progress."""
        data = None
        
        if self._ensure_connection():
            try:
                key = f"progress:{job_id}"
                raw = self._redis_client.get(key)
                if raw:
                    data = json.loads(raw)
            except Exception as e:
                logger.error(f"Redis error getting progress: {e}")
        
        # Fallback to in-memory
        if data is None:
            data = self._fallback_progress.get(job_id)
        
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
    
    # ============ Result Storage ============
    
    def set_result(self, job_id: str, report: DiffReport):
        """Store job result."""
        data = report.model_dump(mode='json')
        
        if self._ensure_connection():
            try:
                key = f"result:{job_id}"
                self._redis_client.setex(key, JOB_EXPIRY_SECONDS, json.dumps(data, default=str))
                return
            except Exception as e:
                logger.error(f"Redis error storing result: {e}")
        
        # Fallback to in-memory
        self._fallback_results[job_id] = data
    
    def get_result(self, job_id: str) -> Optional[DiffReport]:
        """Get job result."""
        data = None
        
        if self._ensure_connection():
            try:
                key = f"result:{job_id}"
                raw = self._redis_client.get(key)
                if raw:
                    data = json.loads(raw)
            except Exception as e:
                logger.error(f"Redis error getting result: {e}")
        
        # Fallback to in-memory
        if data is None:
            data = self._fallback_results.get(job_id)
        
        if data:
            # Handle datetime parsing
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            if 'completed_at' in data and isinstance(data['completed_at'], str):
                data['completed_at'] = datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00'))
            return DiffReport(**data)
        return None
    
    def has_result(self, job_id: str) -> bool:
        """Check if job result exists."""
        if self._ensure_connection():
            try:
                key = f"result:{job_id}"
                return self._redis_client.exists(key) > 0
            except Exception as e:
                logger.error(f"Redis error checking result: {e}")
        
        return job_id in self._fallback_results
    
    def delete_job(self, job_id: str):
        """Delete job data."""
        if self._ensure_connection():
            try:
                self._redis_client.delete(f"progress:{job_id}", f"result:{job_id}")
            except Exception as e:
                logger.error(f"Redis error deleting job: {e}")
        
        self._fallback_progress.pop(job_id, None)
        self._fallback_results.pop(job_id, None)
    
    # ============ Utility Methods ============
    
    def list_jobs(self, pattern: str = "*") -> list:
        """List all job IDs matching pattern."""
        jobs = set()
        
        if self._ensure_connection():
            try:
                for key in self._redis_client.scan_iter(f"result:{pattern}"):
                    job_id = key.replace("result:", "")
                    jobs.add(job_id)
            except Exception as e:
                logger.error(f"Redis error listing jobs: {e}")
        
        # Add fallback jobs
        jobs.update(self._fallback_results.keys())
        
        return list(jobs)
    
    def get_stats(self) -> dict:
        """Get storage statistics."""
        stats = {
            "using_redis": self._use_redis,
            "fallback_results_count": len(self._fallback_results),
            "fallback_progress_count": len(self._fallback_progress),
        }
        
        if self._ensure_connection():
            try:
                stats["redis_results_count"] = len(list(self._redis_client.scan_iter("result:*")))
                stats["redis_progress_count"] = len(list(self._redis_client.scan_iter("progress:*")))
            except:
                pass
        
        return stats


# Global instance
job_storage = JobStorage()
