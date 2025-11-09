"""Unified setup script for the Gradent study assistant.

This script sets up everything needed for development:
1. Initializes/migrates the SQL database schema
2. Populates mock data (users, courses, assignments)
3. Populates vector database with assignment documents
4. Creates sample suggestions

Run this to get a clean development environment ready to use.
"""
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path so we can import from root modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db, get_db_session, get_db_path
from database import mock_data
from database.models import User, Assignment, UserAssignment, AssignmentStatus
from vector_db import get_vector_store, ingest_document, get_vector_db_path
from vector_db.mock_documents import get_all_mock_assignments
from vector_db.retrieval import get_collection_stats


def print_section_header(title: str, char: str = "="):
    """Print a formatted section header."""
    width = 70
    print("\n" + char * width)
    print(title.center(width))
    print(char * width + "\n")


def print_step(step_num: int, description: str):
    """Print a step description."""
    print(f"{step_num}. {description}")


def print_substep(description: str, status: str = "OK"):
    """Print a substep with status."""
    status_marker = "✓" if status == "OK" else "⚠" if status == "WARN" else "✗"
    print(f"   [{status_marker}] {description}")


def setup_sql_database(reset: bool = False) -> bool:
    """Initialize SQL database and schema.
    
    Args:
        reset: If True, clears all existing data
        
    Returns:
        True if successful
    """
    print_step(1, "Setting up SQL Database")
    
    db_path = get_db_path()
    
    if reset and db_path.exists():
        print_substep("Clearing existing database...", "WARN")
        db_path.unlink()
    
    # Initialize database schema
    init_db()
    print_substep(f"Database initialized at: {db_path}")
    
    return True


def populate_mock_data() -> bool:
    """Populate database with mock users, courses, and assignments.
    
    Returns:
        True if successful
    """
    print_step(2, "Populating Mock Data")
    
    try:
        # Clear existing data
        mock_data.clear_all_data()
        print_substep("Cleared existing data")
        
        # Populate new data
        mock_data.populate_mock_data()
        print_substep("Created mock users, courses, and assignments")
        
        # Verify data
        with get_db_session() as db:
            user_count = db.query(User).count()
            assignment_count = db.query(Assignment).count()
            user_assignment_count = db.query(UserAssignment).count()
            
            print_substep(f"Created {user_count} user(s)")
            print_substep(f"Created {assignment_count} assignment(s)")
            print_substep(f"Created {user_assignment_count} user assignment(s)")
        
        return True
    except Exception as e:
        print_substep(f"Error: {e}", "ERROR")
        return False


def populate_suggestions(user_id: int = 1) -> bool:
    """Populate sample suggestions for user.
    
    Args:
        user_id: Target user ID
        
    Returns:
        True if successful
    """
    print_step(3, "Creating Sample Suggestions")
    
    try:
        from datetime import datetime, timedelta
        from database.models import Suggestion, SuggestionStatus
        
        SAMPLE_SUGGESTIONS = [
            {
                "title": "Kick off MDP Implementation",
                "message": "Block 90 minutes to read the MDP chapter and list milestones for value/policy iteration.",
                "category": "deadline_reminder",
                "priority": "high",
                "suggested_time": datetime.utcnow() + timedelta(hours=1),
                "tags": ["mdp", "rl"],
                "linked_assignments": [1],
            },
            {
                "title": "Resource review: Hybrid Images",
                "message": "Skim the hybrid-images doc to refresh Gaussian/Laplacian pyramids before coding.",
                "category": "resource_recommendation",
                "priority": "medium",
                "suggested_time": datetime.utcnow() + timedelta(hours=2),
                "tags": ["cv"],
                "linked_assignments": [5],
            },
            {
                "title": "Plan Supervised Learning sessions",
                "message": "Schedule 2-3 focused blocks to make progress on preprocessing and experiments.",
                "category": "schedule_gap",
                "priority": "medium",
                "suggested_time": datetime.utcnow() + timedelta(hours=3),
                "tags": ["ml"],
                "linked_assignments": [3],
            },
        ]
        
        with get_db_session() as db:
            # Clear existing suggestions
            db.query(Suggestion).filter_by(user_id=user_id).delete()
            
            # Add new suggestions
            for item in SAMPLE_SUGGESTIONS:
                suggestion = Suggestion(
                    user_id=user_id,
                    title=item["title"],
                    message=item["message"],
                    category=item["category"],
                    priority=item["priority"],
                    suggested_time=item["suggested_time"],
                    suggested_time_text=None,
                    tags=item["tags"],
                    linked_assignments=item["linked_assignments"],
                    linked_events=[],
                    sources=[],
                    channel_config={},
                    status=SuggestionStatus.PENDING,
                )
                db.add(suggestion)
            
            db.flush()
            count = db.query(Suggestion).filter_by(user_id=user_id).count()
            print_substep(f"Created {count} sample suggestion(s) for user {user_id}")
        
        return True
    except Exception as e:
        print_substep(f"Error: {e}", "ERROR")
        return False


def setup_vector_database(reset: bool = False) -> bool:
    """Initialize and populate vector database.
    
    Args:
        reset: If True, clears existing vector DB
        
    Returns:
        True if successful
    """
    print_step(4, "Setting up Vector Database")
    
    try:
        # Initialize vector store
        vector_store = get_vector_store(reset=reset)
        if reset:
            print_substep("Cleared existing vector database", "WARN")
        print_substep(f"Vector DB at: {get_vector_db_path()}")
        
        # Get mock assignments
        mock_assignments = get_all_mock_assignments()
        
        # Map assignment keys to database IDs
        assignment_mapping = {
            "rl_mdp_assignment": {"assignment_id": 1, "course_id": 1, "user_id": 1},
            "ml_supervised_learning": {"assignment_id": 3, "course_id": 2, "user_id": 1},
            "cv_hybrid_images": {"assignment_id": 5, "course_id": 3, "user_id": 1},
        }
        
        # Ingest each assignment
        total_chunks = 0
        for key, doc in mock_assignments.items():
            metadata = assignment_mapping.get(key, {"user_id": 1})
            
            ids = ingest_document(
                text=doc['content'],
                doc_id=f"assignment_{key}",
                source_type="assignment",
                user_id=metadata.get("user_id"),
                course_id=metadata.get("course_id"),
                assignment_id=metadata.get("assignment_id"),
                additional_metadata={
                    "title": doc['title'],
                    "course": doc['course'],
                },
                chunk_size=800,
                chunk_overlap=150
            )
            
            total_chunks += len(ids)
            print_substep(f"{doc['title']}: {len(ids)} chunks")
        
        # Show statistics
        stats = get_collection_stats()
        print_substep(f"Total chunks in vector DB: {stats['total_chunks']}")
        
        return True
    except Exception as e:
        print_substep(f"Error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def verify_setup() -> bool:
    """Verify that all components are set up correctly.
    
    Returns:
        True if all checks pass
    """
    print_step(5, "Verifying Setup")
    
    all_good = True
    
    # Check SQL database
    try:
        with get_db_session() as db:
            user_count = db.query(User).count()
            assignment_count = db.query(Assignment).count()
            
            if user_count > 0 and assignment_count > 0:
                print_substep(f"SQL DB: {user_count} users, {assignment_count} assignments")
            else:
                print_substep("SQL DB: No data found", "WARN")
                all_good = False
    except Exception as e:
        print_substep(f"SQL DB Error: {e}", "ERROR")
        all_good = False
    
    # Check vector database
    try:
        stats = get_collection_stats()
        if stats['total_chunks'] > 0:
            print_substep(f"Vector DB: {stats['total_chunks']} chunks")
        else:
            print_substep("Vector DB: No chunks found", "WARN")
            all_good = False
    except Exception as e:
        print_substep(f"Vector DB Error: {e}", "ERROR")
        all_good = False
    
    return all_good


def main():
    """Run the complete setup process."""
    print_section_header("Gradent Study Assistant - Complete Setup")
    
    print("This script will set up:")
    print("  • SQL Database (users, courses, assignments)")
    print("  • Mock data for development")
    print("  • Vector database with assignment documents")
    print("  • Sample suggestions")
    print()
    
    # Ask user preferences
    reset_all = False
    if '--reset' in sys.argv or '--full-reset' in sys.argv:
        reset_all = True
        print("⚠ FULL RESET MODE: All existing data will be cleared!")
    else:
        response = input("Clear existing data and start fresh? (y/n): ")
        reset_all = response.lower() == 'y'
    
    if reset_all:
        print("\n⚠ This will DELETE all existing data!")
        response = input("Are you sure? Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("\nSetup cancelled.")
            return 1
    
    print()
    
    # Run setup steps
    success = True
    
    success = setup_sql_database(reset=reset_all) and success
    success = populate_mock_data() and success
    success = populate_suggestions(user_id=1) and success
    success = setup_vector_database(reset=reset_all) and success
    success = verify_setup() and success
    
    # Final message
    if success:
        print_section_header("✓ Setup Complete!", "=")
        print("Your development environment is ready!")
        print()
        print("Next steps:")
        print("  1. Run the application: poetry run python main.py")
        print("  2. Or run tests: poetry run pytest")
        print("  3. Check the database: poetry run python verify_db.py")
        print()
        return 0
    else:
        print_section_header("✗ Setup Failed", "=")
        print("Some steps encountered errors. Please check the output above.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
