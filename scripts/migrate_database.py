"""Database schema update script.

This script migrates the database to the new schema with:
- UserAssignment table (user-specific assignment tracking)
- StudyHistory table (progress logging)
- StudyBlock table (scheduled study sessions)

It also migrates existing Assignment data to UserAssignment.
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db, get_db_session, User, Assignment, UserAssignment, AssignmentStatus


def migrate_existing_data():
    """Migrate existing assignment data to user assignments."""
    print("\n" + "=" * 70)
    print("Database Schema Migration")
    print("=" * 70 + "\n")
    
    # Initialize database (creates new tables)
    print("1. Initializing database schema...")
    init_db()
    print("   [OK] Database schema updated\n")
    
    # Migrate existing data
    print("2. Migrating existing assignment data to UserAssignment...")
    
    with get_db_session() as db:
        # Get all users
        users = db.query(User).all()
        print(f"   Found {len(users)} user(s)")
        
        if not users:
            print("   [WARN] No users found - skipping migration")
            print("\n[OK] Migration complete!")
            return
        
        # For each user, get their assignments through courses
        migrated_count = 0
        for user in users:
            print(f"\n   Migrating data for user: {user.name} (ID: {user.id})")
            
            # Get all assignments for user's courses
            user_course_ids = [course.id for course in user.courses]
            if not user_course_ids:
                print("     No courses found for this user")
                continue
            
            assignments = db.query(Assignment).filter(
                Assignment.course_id.in_(user_course_ids)
            ).all()
            
            print(f"     Found {len(assignments)} assignment(s)")
            
            for assignment in assignments:
                # Check if UserAssignment already exists
                existing = db.query(UserAssignment).filter_by(
                    user_id=user.id,
                    assignment_id=assignment.id
                ).first()
                
                if existing:
                    print(f"       - {assignment.title}: Already migrated")
                    continue
                
                # Create new UserAssignment
                user_assignment = UserAssignment(
                    user_id=user.id,
                    assignment_id=assignment.id,
                    status=AssignmentStatus.NOT_STARTED,
                    hours_done=0.0,
                )
                
                db.add(user_assignment)
                migrated_count += 1
                print(f"       - {assignment.title}: Migrated")
            
            db.flush()
        
        print(f"\n   [OK] Migrated {migrated_count} assignment(s) to UserAssignment")
    
    print("\n" + "=" * 70)
    print("[OK] Migration complete!")
    print("=" * 70)
    print("\nNew tables created:")
    print("  - user_assignments (user-specific assignment tracking)")
    print("  - study_history (progress logs)")
    print("  - study_blocks (scheduled study sessions)")
    print()


if __name__ == "__main__":
    migrate_existing_data()
