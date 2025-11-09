"""Database migration script to add CalendarEvent table.

This script adds the calendar_events table to track calendar events
created by the scheduler agent.
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db


def migrate_calendar_events():
    """Add CalendarEvent table to the database."""
    print("\n" + "=" * 70)
    print("Calendar Events Table Migration")
    print("=" * 70 + "\n")
    
    # Initialize database (creates new tables including calendar_events)
    print("1. Adding calendar_events table to database schema...")
    init_db()
    print("   [OK] calendar_events table created\n")
    
    print("[OK] Migration complete!")
    print("\nThe calendar_events table is now available for tracking scheduled events.")


if __name__ == "__main__":
    migrate_calendar_events()
