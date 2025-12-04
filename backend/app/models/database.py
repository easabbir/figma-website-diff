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
            user_id TEXT,
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
    
    # Add user_id column if it doesn't exist (migration for existing databases)
    try:
        cursor.execute("ALTER TABLE comparisons ADD COLUMN user_id TEXT")
    except:
        pass  # Column already exists
    
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
            comparison_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    
    # Add comparison_count column if it doesn't exist (migration for existing databases)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN comparison_count INTEGER DEFAULT 0")
    except:
        pass  # Column already exists
    
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
                       tags: Optional[List[str]] = None,
                       user_id: Optional[str] = None) -> str:
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
                id, job_id, user_id, figma_url, website_url, 
                viewport_width, viewport_height, viewport_name,
                project_name, tags, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            comparison_id,
            job_id,
            user_id,
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
        
        logger.info(f"Saved comparison {comparison_id} to history for user {user_id}")
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
                   status: Optional[str] = None,
                   user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get comparison history with optional filters.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            website_url: Filter by website URL
            project_name: Filter by project name
            status: Filter by status
            user_id: Filter by user ID (for privacy)
            
        Returns:
            List of comparison records
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM comparisons WHERE 1=1"
        params = []
        
        # Filter by user_id for privacy
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
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
    
    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get overall statistics for a user."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_comparisons,
                    AVG(match_score) as avg_match_score,
                    SUM(total_differences) as total_differences_found,
                    COUNT(DISTINCT website_url) as unique_websites
                FROM comparisons
                WHERE status = 'completed' AND user_id = ?
            """, (user_id,))
        else:
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
    
    def delete_comparison(self, job_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a comparison from history (only if owned by user)."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("DELETE FROM comparisons WHERE job_id = ? AND user_id = ?", (job_id, user_id))
        else:
            cursor.execute("DELETE FROM comparisons WHERE job_id = ?", (job_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def delete_all(self, user_id: Optional[str] = None) -> int:
        """Delete all comparisons from history for a user."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user_id:
            # Get comparison IDs for this user
            cursor.execute("SELECT id FROM comparisons WHERE user_id = ?", (user_id,))
            comparison_ids = [row[0] for row in cursor.fetchall()]
            
            if comparison_ids:
                # Delete viewport results for these comparisons
                placeholders = ','.join('?' * len(comparison_ids))
                cursor.execute(f"DELETE FROM viewport_results WHERE comparison_id IN ({placeholders})", comparison_ids)
                # Delete comparisons
                cursor.execute(f"DELETE FROM comparisons WHERE user_id = ?", (user_id,))
            count = len(comparison_ids)
        else:
            # Delete all (admin only)
            cursor.execute("DELETE FROM viewport_results")
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
    
    def increment_comparison_count(self, user_id: str) -> int:
        """
        Increment the comparison count for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            The new comparison count
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET comparison_count = comparison_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))
        
        conn.commit()
        
        # Get the new count
        cursor.execute("SELECT comparison_count FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        return row['comparison_count'] if row else 0
    
    def get_comparison_count(self, user_id: str) -> int:
        """Get the comparison count for a user."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT comparison_count FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        return row['comparison_count'] if row else 0


# Global instances
history_db = ComparisonHistory()
user_db = UserDB()
