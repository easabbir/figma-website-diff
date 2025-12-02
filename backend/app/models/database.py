"""Database models for comparison history using SQLite."""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "comparison_history.db"


def get_db_connection():
    """Get database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create comparisons table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comparisons (
            id TEXT PRIMARY KEY,
            job_id TEXT UNIQUE NOT NULL,
            figma_url TEXT,
            website_url TEXT NOT NULL,
            viewport_width INTEGER DEFAULT 1920,
            viewport_height INTEGER DEFAULT 1080,
            viewport_name TEXT DEFAULT 'desktop',
            match_score REAL DEFAULT 0.0,
            total_differences INTEGER DEFAULT 0,
            critical_count INTEGER DEFAULT 0,
            warning_count INTEGER DEFAULT 0,
            info_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            report_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            project_name TEXT,
            tags TEXT
        )
    """)
    
    # Create viewport_results table for responsive mode
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS viewport_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comparison_id TEXT NOT NULL,
            viewport_name TEXT NOT NULL,
            viewport_width INTEGER NOT NULL,
            viewport_height INTEGER NOT NULL,
            match_score REAL DEFAULT 0.0,
            total_differences INTEGER DEFAULT 0,
            figma_screenshot_url TEXT,
            website_screenshot_url TEXT,
            visual_diff_url TEXT,
            report_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (comparison_id) REFERENCES comparisons(id)
        )
    """)
    
    # Create users table for authentication
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comparisons_created_at 
        ON comparisons(created_at DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comparisons_website_url 
        ON comparisons(website_url)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email 
        ON users(email)
    """)
    
    conn.commit()
    conn.close()
    
    logger.info(f"Database initialized at {DB_PATH}")


class ComparisonHistory:
    """Manage comparison history in SQLite database."""
    
    def __init__(self):
        init_database()
    
    def save_comparison(self, 
                       job_id: str,
                       figma_url: str,
                       website_url: str,
                       viewport: Dict[str, int],
                       viewport_name: str = "desktop",
                       project_name: Optional[str] = None,
                       tags: Optional[List[str]] = None) -> str:
        """
        Save a new comparison to history.
        
        Returns:
            The comparison ID
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        comparison_id = job_id
        
        cursor.execute("""
            INSERT INTO comparisons (
                id, job_id, figma_url, website_url, 
                viewport_width, viewport_height, viewport_name,
                project_name, tags, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            comparison_id,
            job_id,
            figma_url,
            website_url,
            viewport.get("width", 1920),
            viewport.get("height", 1080),
            viewport_name,
            project_name,
            json.dumps(tags) if tags else None,
            "processing"
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved comparison {comparison_id} to history")
        return comparison_id
    
    def update_comparison_result(self,
                                job_id: str,
                                match_score: float,
                                total_differences: int,
                                critical_count: int,
                                warning_count: int,
                                info_count: int,
                                report_json: Optional[str] = None,
                                status: str = "completed"):
        """Update comparison with results."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE comparisons SET
                match_score = ?,
                total_differences = ?,
                critical_count = ?,
                warning_count = ?,
                info_count = ?,
                report_json = ?,
                status = ?,
                completed_at = ?
            WHERE job_id = ?
        """, (
            match_score,
            total_differences,
            critical_count,
            warning_count,
            info_count,
            report_json,
            status,
            datetime.now().isoformat(),
            job_id
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated comparison {job_id} with results")
    
    def get_comparison(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a single comparison by job ID."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM comparisons WHERE job_id = ?
        """, (job_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_history(self, 
                   limit: int = 50,
                   offset: int = 0,
                   website_url: Optional[str] = None,
                   project_name: Optional[str] = None,
                   status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get comparison history with optional filters.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            website_url: Filter by website URL
            project_name: Filter by project name
            status: Filter by status
            
        Returns:
            List of comparison records
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM comparisons WHERE 1=1"
        params = []
        
        if website_url:
            query += " AND website_url LIKE ?"
            params.append(f"%{website_url}%")
        
        if project_name:
            query += " AND project_name = ?"
            params.append(project_name)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_comparisons,
                AVG(match_score) as avg_match_score,
                SUM(total_differences) as total_differences_found,
                COUNT(DISTINCT website_url) as unique_websites
            FROM comparisons
            WHERE status = 'completed'
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else {}
    
    def delete_comparison(self, job_id: str) -> bool:
        """Delete a comparison from history."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM comparisons WHERE job_id = ?", (job_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def delete_all(self) -> int:
        """Delete all comparisons from history."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete viewport results first (foreign key)
        cursor.execute("DELETE FROM viewport_results")
        # Delete all comparisons
        cursor.execute("DELETE FROM comparisons")
        count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return count
    
    def save_viewport_result(self,
                            comparison_id: str,
                            viewport_name: str,
                            viewport_width: int,
                            viewport_height: int,
                            match_score: float,
                            total_differences: int,
                            figma_screenshot_url: Optional[str] = None,
                            website_screenshot_url: Optional[str] = None,
                            visual_diff_url: Optional[str] = None,
                            report_json: Optional[str] = None):
        """Save viewport-specific result for responsive mode."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO viewport_results (
                comparison_id, viewport_name, viewport_width, viewport_height,
                match_score, total_differences, figma_screenshot_url,
                website_screenshot_url, visual_diff_url, report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            comparison_id,
            viewport_name,
            viewport_width,
            viewport_height,
            match_score,
            total_differences,
            figma_screenshot_url,
            website_screenshot_url,
            visual_diff_url,
            report_json
        ))
        
        conn.commit()
        conn.close()
    
    def get_viewport_results(self, comparison_id: str) -> List[Dict[str, Any]]:
        """Get all viewport results for a comparison."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM viewport_results 
            WHERE comparison_id = ?
            ORDER BY viewport_width ASC
        """, (comparison_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


class UserDB:
    """Manage users in SQLite database."""
    
    def __init__(self):
        init_database()
    
    def create_user(self, user_id: str, email: str, password_hash: str, 
                   full_name: Optional[str] = None) -> bool:
        """Create a new user. Returns True if successful."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, full_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, email.lower(), password_hash, full_name))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Email already exists
            return False
        finally:
            conn.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM users WHERE email = ?
        """, (email.lower(),))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM users WHERE id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user fields."""
        if not kwargs:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build update query
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ['full_name', 'is_active']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(user_id)
        
        cursor.execute(f"""
            UPDATE users SET {', '.join(fields)} WHERE id = ?
        """, values)
        
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        
        return updated


# Global instances
history_db = ComparisonHistory()
user_db = UserDB()
