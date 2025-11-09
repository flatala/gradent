"""Rebuild the database with fresh mock data.

This script:
1. Backs up existing database (if it exists)
2. Deletes the database
3. Initializes fresh database with schema
4. Populates with mock data

Use this when you need to reset to a clean state.
"""
import sys
from pathlib import Path
import shutil
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db
from database.connection import DB_PATH
from database.mock_data import populate_mock_data


def backup_database(db_path: Path):
    """Create a backup of the existing database."""
    if db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
        shutil.copy2(db_path, backup_path)
        print(f"[OK] Backed up database to: {backup_path}")
        return backup_path
    return None


def main():
    """Rebuild the database."""
    print("\n" + "=" * 70)
    print("DATABASE REBUILD")
    print("=" * 70 + "\n")
    
    # Get database path
    db_path = Path(DB_PATH)
    
    print(f"Database path: {db_path}")
    
    # Step 1: Backup existing database
    if db_path.exists():
        print("\nStep 1: Backing up existing database...")
        backup_database(db_path)
        
        # Step 2: Delete old database
        print("\nStep 2: Deleting old database...")
        db_path.unlink()
        print("[OK] Deleted old database")
    else:
        print("\nNo existing database found, creating fresh...")
    
    # Step 3: Initialize fresh database
    print("\nStep 3: Initializing fresh database schema...")
    init_db()
    print("[OK] Database schema created")
    
    # Step 4: Populate with mock data
    print("\nStep 4: Populating with mock data...")
    stats = populate_mock_data()
    print("[OK] Mock data populated")
    
    # Summary
    print("\n" + "=" * 70)
    print("DATABASE REBUILD COMPLETE")
    print("=" * 70)
    print("\nMock Data Summary:")
    print(f"  Users: {stats.get('users', 0)}")
    print(f"  Courses: {stats.get('courses', 0)}")
    print(f"  Assignments: {stats.get('assignments', 0)}")
    print(f"  Assessments: {stats.get('assessments', 0)}")
    print(f"  User Assignments: {stats.get('user_assignments', 0)}")
    
    print("\n[OK] Database is ready for testing!")
    print("\nNote: Mock data has [MOCK DB] prefix in assignment titles")
    print("      Brightspace sync will add [BRIGHTSPACE] prefix")
    print("      This makes it easy to distinguish the source of data\n")


if __name__ == "__main__":
    main()
