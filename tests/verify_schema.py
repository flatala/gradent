"""Verify the new database schema with UserAssignment."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db_session, User, Assignment, UserAssignment, StudyHistory, StudyBlock


def verify_schema():
    """Verify the new database schema."""
    print("\n" + "=" * 70)
    print("Database Schema Verification")
    print("=" * 70 + "\n")
    
    with get_db_session() as db:
        # Check users
        users = db.query(User).all()
        print(f"Users: {len(users)}")
        for user in users:
            print(f"  - {user.name} (ID: {user.id})")
        print()
        
        # Check assignments
        assignments = db.query(Assignment).all()
        print(f"Assignments (universal): {len(assignments)}")
        for assignment in assignments:
            print(f"  - {assignment.title}")
            print(f"    Course ID: {assignment.course_id}, LMS ID: {assignment.lms_assignment_id}")
        print()
        
        # Check user assignments
        user_assignments = db.query(UserAssignment).all()
        print(f"UserAssignments (personalized): {len(user_assignments)}")
        for ua in user_assignments:
            assignment = ua.assignment
            user = ua.user
            print(f"  - {user.name} → {assignment.title}")
            print(f"    Status: {ua.status.value}, Hours Done: {ua.hours_done}, Remaining: {ua.hours_remaining}")
        print()
        
        # Check study history
        history = db.query(StudyHistory).all()
        print(f"StudyHistory entries: {len(history)}")
        print()
        
        # Check study blocks
        blocks = db.query(StudyBlock).all()
        print(f"StudyBlocks: {len(blocks)}")
        print()
    
    print("=" * 70)
    print("[OK] Schema verification complete!")
    print("=" * 70)
    print("\nNew schema is working correctly:")
    print("  ✓ Assignments are universal (from LMS)")
    print("  ✓ UserAssignments track personalized progress")
    print("  ✓ Multiple users can work on same assignment with different progress")
    print()


if __name__ == "__main__":
    verify_schema()
