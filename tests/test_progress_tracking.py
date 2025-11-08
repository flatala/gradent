"""
Test for progress tracking workflow.
Tests log_study_progress, get_assignment_progress, and get_user_study_summary.
"""
from datetime import datetime, timedelta
from sqlalchemy import select
from database import init_db, get_db_session
from database.models import User, Course, Assignment, UserAssignment, StudyHistory, StudyBlock
from workflows.progress_tracking import (
    log_study_progress,
    get_assignment_progress,
    get_user_study_summary,
    parse_progress_from_text
)


def setup_test_data():
    """Create test user, course, assignments, and user assignments."""
    print("Setting up test data...")
    
    with get_db_session() as session:
        # Create test user
        user = User(
            name="Test Student",
            email="test@example.com",
            lms_user_id="test_lms_123"
        )
        session.add(user)
        session.flush()
        
        # Create test course
        course = Course(
            name="Introduction to AI",
            lms_course_id="ai_101",
            lms_course_name="AI 101"
        )
        session.add(course)
        session.flush()
        
        # Create test assignments
        assignments = []
        for i in range(3):
            assignment = Assignment(
                course_id=course.id,
                name=f"Assignment {i+1}",
                instructions=f"Complete assignment {i+1}",
                deadline=datetime.now() + timedelta(days=7*(i+1)),
                lms_assignment_id=f"assign_{i+1}",
                weight_percentage=30.0
            )
            session.add(assignment)
            session.flush()
            assignments.append(assignment)
            
            # Create UserAssignment with some initial hours
            ua = UserAssignment(
                user_id=user.id,
                assignment_id=assignment.id,
                status="NOT_STARTED",
                hours_done=0.0,
                hours_remaining=10.0 if i == 0 else 8.0  # First assignment has 10h, others 8h
            )
            session.add(ua)
        
        session.commit()
        
        print(f"Created user: {user.id}")
        print(f"Created course: {course.id}")
        print(f"Created {len(assignments)} assignments with UserAssignments")
        
        return user.id, course.id, [a.id for a in assignments]


def test_log_study_progress(user_id: int, assignment_ids: list):
    """Test logging study progress."""
    print("\n=== Test 1: Log Study Progress ===")
    
    assignment_id = assignment_ids[0]
    
    # Log first study session
    result = log_study_progress(
        user_id=user_id,
        assignment_id=assignment_id,
        minutes=90,
        focus_rating_1to5=4,
        quality_rating_1to5=4,
        notes="Worked on understanding the problem requirements"
    )
    
    print(f"Session 1 logged: {result['success']}")
    print(f"Hours logged: {result['hours_logged']}")
    print(f"Assignment progress: {result['assignment_progress']}")
    
    assert result['success'], "First session should succeed"
    assert result['hours_logged'] == 1.5, "Should log 1.5 hours"
    
    # Log second study session
    result = log_study_progress(
        user_id=user_id,
        assignment_id=assignment_id,
        minutes=120,
        focus_rating_1to5=5,
        quality_rating_1to5=3,
        notes="Implemented main algorithm, got stuck on edge cases"
    )
    
    print(f"\nSession 2 logged: {result['success']}")
    print(f"Total hours done: {result['assignment_progress']['hours_done']}")
    print(f"Hours remaining: {result['assignment_progress']['hours_remaining']}")
    print(f"Status: {result['assignment_progress']['status']}")
    
    assert result['success'], "Second session should succeed"
    assert result['assignment_progress']['hours_done'] == 3.5, "Should have 3.5 hours total"
    assert result['assignment_progress']['status'] == "IN_PROGRESS", "Should be in progress"
    
    # Verify StudyHistory entries were created
    with get_db_session() as session:
        stmt = select(StudyHistory).where(
            StudyHistory.user_id == user_id,
            StudyHistory.assignment_id == assignment_id
        )
        history_entries = session.execute(stmt).scalars().all()
        
        print(f"\nTotal StudyHistory entries: {len(history_entries)}")
        assert len(history_entries) == 2, "Should have 2 history entries"
        
        # Check latest entry
        latest = history_entries[-1]
        assert latest.minutes == 120, "Latest entry should be 120 minutes"
        assert latest.focus_rating_1to5 == 5, "Latest entry should have focus 5"
        assert latest.quality_rating_1to5 == 3, "Latest entry should have quality 3"
        
    print("✅ Test 1 passed!")


def test_get_assignment_progress(user_id: int, assignment_ids: list):
    """Test getting assignment progress."""
    print("\n=== Test 2: Get Assignment Progress ===")
    
    assignment_id = assignment_ids[0]
    
    progress = get_assignment_progress(user_id, assignment_id)
    
    print(f"Assignment progress:")
    print(f"  Hours done: {progress['hours_done']}")
    print(f"  Hours remaining: {progress['hours_remaining']}")
    print(f"  Status: {progress['status']}")
    print(f"  Total sessions: {progress['total_sessions']}")
    print(f"  Recent focus avg: {progress['recent_focus_avg']}")
    print(f"  Recent quality avg: {progress['recent_quality_avg']}")
    
    assert progress['hours_done'] == 3.5, "Should have 3.5 hours done"
    assert progress['total_sessions'] == 2, "Should have 2 sessions"
    assert progress['recent_focus_avg'] == 4.5, "Recent focus should be (4+5)/2 = 4.5"
    assert progress['recent_quality_avg'] == 3.5, "Recent quality should be (4+3)/2 = 3.5"
    
    print("✅ Test 2 passed!")


def test_multiple_assignments(user_id: int, assignment_ids: list):
    """Test logging progress on multiple assignments."""
    print("\n=== Test 3: Multiple Assignments ===")
    
    # Log sessions on second assignment
    for i in range(3):
        result = log_study_progress(
            user_id=user_id,
            assignment_id=assignment_ids[1],
            minutes=60,
            focus_rating_1to5=3,
            quality_rating_1to5=4,
            notes=f"Session {i+1} on assignment 2"
        )
        print(f"Assignment 2, session {i+1}: {result['hours_logged']}h logged")
    
    # Log one session on third assignment
    result = log_study_progress(
        user_id=user_id,
        assignment_id=assignment_ids[2],
        minutes=45,
        focus_rating_1to5=5,
        quality_rating_1to5=5,
        notes="Quick focused session"
    )
    print(f"Assignment 3, session 1: {result['hours_logged']}h logged")
    
    print("✅ Test 3 passed!")


def test_get_user_study_summary(user_id: int):
    """Test getting user study summary."""
    print("\n=== Test 4: User Study Summary ===")
    
    summary = get_user_study_summary(user_id, days=7)
    
    print(f"Study summary (last 7 days):")
    print(f"  Total minutes: {summary['total_minutes']}")
    print(f"  Total sessions: {summary['total_sessions']}")
    print(f"  Assignments worked on: {summary['assignments_worked_on']}")
    print(f"  Average focus: {summary['avg_focus']:.2f}")
    print(f"  Average quality: {summary['avg_quality']:.2f}")
    print(f"\n  Top assignments:")
    for i, assign in enumerate(summary['top_assignments'], 1):
        print(f"    {i}. {assign['assignment_name']}: {assign['minutes']}min, {assign['sessions']} sessions")
    
    # Verify totals
    # Assignment 1: 90 + 120 = 210 min
    # Assignment 2: 60 * 3 = 180 min
    # Assignment 3: 45 min
    # Total: 435 min, 6 sessions, 3 assignments
    
    assert summary['total_minutes'] == 435, "Total minutes should be 435"
    assert summary['total_sessions'] == 6, "Total sessions should be 6"
    assert summary['assignments_worked_on'] == 3, "Should have worked on 3 assignments"
    assert len(summary['top_assignments']) == 3, "Should list all 3 assignments"
    
    # Top assignment should be Assignment 1 with 210 minutes
    top = summary['top_assignments'][0]
    assert top['minutes'] == 210, "Top assignment should have 210 minutes"
    assert top['sessions'] == 2, "Top assignment should have 2 sessions"
    
    print("✅ Test 4 passed!")


def test_study_block_integration(user_id: int, assignment_ids: list):
    """Test that logging progress updates StudyBlock if linked."""
    print("\n=== Test 5: StudyBlock Integration ===")
    
    assignment_id = assignment_ids[0]
    
    # Create a study block for this assignment
    with get_db_session() as session:
        study_block = StudyBlock(
            user_id=user_id,
            assignment_id=assignment_id,
            start_at=datetime.now() - timedelta(hours=2),
            end_at=datetime.now() - timedelta(hours=1),
            planned_minutes=60,
            status="SCHEDULED"
        )
        session.add(study_block)
        session.commit()
        block_id = study_block.id
        print(f"Created StudyBlock {block_id} with 60 planned minutes")
    
    # Log progress linked to this block
    result = log_study_progress(
        user_id=user_id,
        assignment_id=assignment_id,
        minutes=55,
        focus_rating_1to5=4,
        quality_rating_1to5=4,
        notes="Completed the scheduled study block",
        study_block_id=block_id
    )
    
    print(f"Logged 55 minutes to block {block_id}")
    
    # Verify block was updated
    with get_db_session() as session:
        stmt = select(StudyBlock).where(StudyBlock.id == block_id)
        block = session.execute(stmt).scalar_one()
        
        print(f"Block actual_minutes: {block.actual_minutes}")
        print(f"Block status: {block.status}")
        
        assert block.actual_minutes == 55, "Block should record 55 actual minutes"
        assert block.status == "COMPLETED", "Block status should be COMPLETED"
    
    print("✅ Test 5 passed!")


def test_parse_progress_from_text(user_id: int):
    """Test natural language parsing helper."""
    print("\n=== Test 6: Parse Progress From Text ===")
    
    test_cases = [
        ("I studied for 90 minutes on the RL assignment and was really focused", {
            'minutes': 90,
            'focus_indicator': 'high',
            'quality_indicator': None
        }),
        ("Worked on assignment 2 for 2 hours, finished the implementation", {
            'minutes': 120,
            'focus_indicator': None,
            'quality_indicator': 'high'
        }),
        ("Quick 30 minute session, got distracted and didn't make much progress", {
            'minutes': 30,
            'focus_indicator': 'low',
            'quality_indicator': 'low'
        }),
        ("Did 1.5 hours of deep work on the project", {
            'minutes': 90,
            'focus_indicator': 'high',
            'quality_indicator': None
        }),
        ("Had lunch", None),  # Not a progress update
    ]
    
    for text, expected in test_cases:
        result = parse_progress_from_text(text, user_id)
        
        if expected is None:
            assert result is None, f"Should not parse: {text}"
            print(f"✓ Correctly ignored: {text}")
        else:
            assert result is not None, f"Should parse: {text}"
            assert result['minutes'] == expected['minutes'], f"Wrong minutes for: {text}"
            assert result['focus_indicator'] == expected['focus_indicator'], f"Wrong focus for: {text}"
            assert result['quality_indicator'] == expected['quality_indicator'], f"Wrong quality for: {text}"
            print(f"✓ Correctly parsed: {text} → {result['minutes']}min, focus={result['focus_indicator']}, quality={result['quality_indicator']}")
    
    print("✅ Test 6 passed!")


def main():
    """Run all tests."""
    print("Initializing database...")
    init_db()
    
    # Setup test data
    user_id, course_id, assignment_ids = setup_test_data()
    
    # Run tests
    test_log_study_progress(user_id, assignment_ids)
    test_get_assignment_progress(user_id, assignment_ids)
    test_multiple_assignments(user_id, assignment_ids)
    test_get_user_study_summary(user_id)
    test_study_block_integration(user_id, assignment_ids)
    test_parse_progress_from_text(user_id)
    
    print("\n" + "="*50)
    print("✅ All progress tracking tests passed!")
    print("="*50)


if __name__ == "__main__":
    main()
