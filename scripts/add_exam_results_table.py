"""Add exam_results table to the database.

Run this script to add the ExamResult model to your existing database.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from database.models import Base, ExamResult
from sqlalchemy import inspect


def add_exam_results_table():
    """Create the exam_results table if it doesn't exist."""
    db = next(get_db())
    engine = db.bind
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if 'exam_results' in existing_tables:
        print("✓ exam_results table already exists")
        db.close()
        return
    
    print("Creating exam_results table...")
    Base.metadata.tables['exam_results'].create(engine)
    print("✓ exam_results table created successfully")
    
    db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Adding exam_results table to database")
    print("=" * 60)
    add_exam_results_table()
    print("\nDone! You can now save exam assessment results.")
