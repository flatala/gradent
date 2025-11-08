"""Test script for Context Updater.

This demonstrates:
1. Syncing courses from Brightspace (mock)
2. Syncing assignments
3. Indexing course materials to vector DB
4. Querying the results from both databases
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from database import get_db_session, User, Course, Assignment
from vector_db.retrieval import get_collection_stats
from context_updater import run_context_update


def setup_test_user():
    """Ensure test user exists in database."""
    with get_db_session() as db:
        user = db.query(User).filter_by(id=1).first()
        if not user:
            user = User(
                id=1,
                name="Alex Student",
                email="alex@example.com",
                timezone="America/New_York",
                preferences={
                    "preferred_study_hours": [9, 10, 11, 14, 15, 16],
                    "max_daily_hours": 6
                }
            )
            db.add(user)
            db.flush()
            print("[OK] Created test user")
        else:
            print(f"[OK] Using existing user: {user.name}")
        return user.id


def query_synced_data():
    """Query and display synced data from normal DB."""
    print("\n" + "=" * 70)
    print("Querying Synced Data from Normal DB")
    print("=" * 70 + "\n")
    
    with get_db_session() as db:
        # Get courses
        courses = db.query(Course).all()
        print(f"Courses: {len(courses)}")
        for course in courses:
            print(f"  - {course.code}: {course.title} ({course.term})")
            print(f"    LMS ID: {course.lms_course_id}")
            
            # Get assignments for this course
            assignments = db.query(Assignment).filter_by(course_id=course.id).all()
            print(f"    Assignments: {len(assignments)}")
            for assignment in assignments:
                due_str = assignment.due_at.strftime("%Y-%m-%d") if assignment.due_at else "No due date"
                print(f"      * {assignment.title} (Due: {due_str})")
            print()


def query_vector_data():
    """Query and display stats from vector DB."""
    print("=" * 70)
    print("Querying Vector DB Stats")
    print("=" * 70 + "\n")
    
    stats = get_collection_stats()
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Source types: {stats['source_types']}")
    
    if stats.get('sample_docs'):
        print(f"\nSample documents:")
        for doc in stats['sample_docs'][:3]:
            metadata = doc.get('metadata', {})
            print(f"  - {metadata.get('title', 'Unknown')}")
            print(f"    Type: {metadata.get('source_type')}, Course: {metadata.get('course_id')}")


def main():
    """Run the context updater test."""
    print("\n" + "=" * 70)
    print("Context Updater Test")
    print("=" * 70 + "\n")
    
    # Setup
    print("Step 1: Setting up test user...")
    user_id = setup_test_user()
    print()
    
    # Run context update
    print("Step 2: Running context update from Brightspace...\n")
    stats = run_context_update(user_id=user_id)
    print()
    
    # Query results from normal DB
    print("Step 3: Verifying data in normal database...")
    query_synced_data()
    print()
    
    # Query results from vector DB
    print("Step 4: Verifying data in vector database...")
    query_vector_data()
    
    print("\n" + "=" * 70)
    print("[OK] Context Updater test complete!")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  Courses synced: {stats['courses_synced']}")
    print(f"  Assignments synced: {stats['assignments_synced']}")
    print(f"  Content chunks indexed: {stats['content_indexed']}")
    print()


if __name__ == "__main__":
    main()
