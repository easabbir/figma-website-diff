#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL.
Run this after setting up PostgreSQL to migrate existing data.

Usage:
    python scripts/migrate_sqlite_to_postgres.py
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.base import engine, SessionLocal, Base
from app.db.models import User, Comparison, ViewportResult

# SQLite database path
SQLITE_DB_PATH = Path(__file__).parent.parent / "data" / "comparison_history.db"


def get_sqlite_connection():
    """Get SQLite database connection."""
    if not SQLITE_DB_PATH.exists():
        print(f"SQLite database not found at {SQLITE_DB_PATH}")
        return None
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def migrate_users(sqlite_conn, pg_session: Session):
    """Migrate users from SQLite to PostgreSQL."""
    print("\n📦 Migrating users...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    
    migrated = 0
    skipped = 0
    
    for row in users:
        # Check if user already exists
        existing = pg_session.query(User).filter(User.id == row['id']).first()
        if existing:
            skipped += 1
            continue
        
        user = User(
            id=row['id'],
            email=row['email'],
            password_hash=row['password_hash'],
            full_name=row['full_name'],
            is_active=bool(row['is_active']) if row['is_active'] is not None else True,
            comparison_count=row['comparison_count'] or 0,
            profile_image=row['profile_image'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
        pg_session.add(user)
        migrated += 1
    
    pg_session.commit()
    print(f"   ✅ Migrated {migrated} users, skipped {skipped} (already exist)")
    return migrated


def migrate_comparisons(sqlite_conn, pg_session: Session):
    """Migrate comparisons from SQLite to PostgreSQL."""
    print("\n📦 Migrating comparisons...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM comparisons")
    comparisons = cursor.fetchall()
    
    migrated = 0
    skipped = 0
    
    for row in comparisons:
        # Check if comparison already exists
        existing = pg_session.query(Comparison).filter(Comparison.job_id == row['job_id']).first()
        if existing:
            skipped += 1
            continue
        
        comparison = Comparison(
            id=row['id'],
            job_id=row['job_id'],
            user_id=row['user_id'],
            comparison_number=row['comparison_number'] if 'comparison_number' in row.keys() else None,
            figma_url=row['figma_url'],
            website_url=row['website_url'],
            viewport_width=row['viewport_width'] or 1920,
            viewport_height=row['viewport_height'] or 1080,
            viewport_name=row['viewport_name'] or 'desktop',
            match_score=row['match_score'] or 0.0,
            total_differences=row['total_differences'] or 0,
            critical_count=row['critical_count'] or 0,
            warning_count=row['warning_count'] or 0,
            info_count=row['info_count'] or 0,
            status=row['status'] or 'pending',
            report_json=row['report_json'],
            project_name=row['project_name'],
            tags=row['tags'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None
        )
        pg_session.add(comparison)
        migrated += 1
    
    pg_session.commit()
    print(f"   ✅ Migrated {migrated} comparisons, skipped {skipped} (already exist)")
    return migrated


def migrate_viewport_results(sqlite_conn, pg_session: Session):
    """Migrate viewport results from SQLite to PostgreSQL."""
    print("\n📦 Migrating viewport results...")
    
    cursor = sqlite_conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='viewport_results'")
    if not cursor.fetchone():
        print("   ⏭️  No viewport_results table found, skipping")
        return 0
    
    cursor.execute("SELECT * FROM viewport_results")
    results = cursor.fetchall()
    
    migrated = 0
    skipped = 0
    
    for row in results:
        # Check if result already exists (by comparison_id and viewport_name)
        existing = pg_session.query(ViewportResult).filter(
            ViewportResult.comparison_id == row['comparison_id'],
            ViewportResult.viewport_name == row['viewport_name']
        ).first()
        if existing:
            skipped += 1
            continue
        
        result = ViewportResult(
            comparison_id=row['comparison_id'],
            viewport_name=row['viewport_name'],
            viewport_width=row['viewport_width'],
            viewport_height=row['viewport_height'],
            match_score=row['match_score'] or 0.0,
            total_differences=row['total_differences'] or 0,
            figma_screenshot_url=row['figma_screenshot_url'],
            website_screenshot_url=row['website_screenshot_url'],
            visual_diff_url=row['visual_diff_url'],
            report_json=row['report_json'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
        )
        pg_session.add(result)
        migrated += 1
    
    pg_session.commit()
    print(f"   ✅ Migrated {migrated} viewport results, skipped {skipped} (already exist)")
    return migrated


def main():
    """Main migration function."""
    print("=" * 60)
    print("🚀 SQLite to PostgreSQL Migration Script")
    print("=" * 60)
    
    # Check SQLite database
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        print("\n❌ No SQLite database found. Nothing to migrate.")
        print("   This is normal for fresh installations.")
        return
    
    # Initialize PostgreSQL tables
    print("\n📦 Initializing PostgreSQL tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   ✅ PostgreSQL tables created/verified")
    except Exception as e:
        print(f"   ❌ Failed to initialize PostgreSQL: {e}")
        print("\n   Make sure PostgreSQL is running and DATABASE_URL is correct.")
        return
    
    # Create session
    pg_session = SessionLocal()
    
    try:
        # Migrate data
        total_users = migrate_users(sqlite_conn, pg_session)
        total_comparisons = migrate_comparisons(sqlite_conn, pg_session)
        total_viewports = migrate_viewport_results(sqlite_conn, pg_session)
        
        print("\n" + "=" * 60)
        print("✅ Migration Complete!")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"   - Users: {total_users}")
        print(f"   - Comparisons: {total_comparisons}")
        print(f"   - Viewport Results: {total_viewports}")
        print(f"\nTotal records migrated: {total_users + total_comparisons + total_viewports}")
        
        # Backup recommendation
        print("\n💡 Recommendation:")
        print(f"   Keep the SQLite database ({SQLITE_DB_PATH}) as a backup")
        print("   until you've verified the PostgreSQL migration is complete.")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        pg_session.rollback()
        raise
    finally:
        pg_session.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
