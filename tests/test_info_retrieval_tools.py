"""Test information retrieval workflow tools for the chat agent."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Standard library imports
import json
from datetime import datetime, timedelta

# Third-party imports
import pytest

# Local imports
from agents.shared.workflow_tools import (
    get_user_assignments,
    get_user_courses,
    get_assignment_assessment,
    get_study_progress,
)
from database.connection import get_db_session
from database.models import (
    User,
    Course,
    Assignment,
    UserAssignment,
    AssignmentStatus,
    AssignmentAssessment,
    StudyHistory,
)


@pytest.fixture
def setup_test_data():
    """Create test data for information retrieval tests."""
    with get_db_session() as db:
        # Clean up any existing test data
        db.query(StudyHistory).filter(StudyHistory.user_id == 1).delete()
        db.query(UserAssignment).filter(UserAssignment.user_id == 1).delete()
        db.query(AssignmentAssessment).delete()
        db.query(Assignment).delete()
        db.query(Course).filter(Course.user_id == 1).delete()
        db.query(User).filter(User.id == 1).delete()
        
        # Create test user
        user = User(id=1, name="Test User", email="test@example.com")
        db.add(user)
        
        # Create test courses
        course1 = Course(
            user_id=1,
            title="Computer Science 101",
            code="CS-101",
            term="Fall 2024"
        )
        course2 = Course(
            user_id=1,
            title="Mathematics 201",
            code="MATH-201",
            term="Fall 2024"
        )
        db.add_all([course1, course2])
        db.flush()
        
        # Create test assignments
        assignment1 = Assignment(
            course_id=course1.id,
            title="Python Programming Project",
            description_short="Build a web scraper",
            due_at=datetime.utcnow() + timedelta(days=7),
            lms_link="https://lms.example.com/assignment1",
            weight_percentage=20.0,
            max_points=100.0
        )
        assignment2 = Assignment(
            course_id=course1.id,
            title="Data Structures Homework",
            description_short="Implement a binary tree",
            due_at=datetime.utcnow() + timedelta(days=3),
            weight_percentage=10.0,
            max_points=50.0
        )
        assignment3 = Assignment(
            course_id=course2.id,
            title="Calculus Problem Set",
            description_short="Integration problems",
            due_at=datetime.utcnow() + timedelta(days=14),
            weight_percentage=15.0,
            max_points=75.0
        )
        db.add_all([assignment1, assignment2, assignment3])
        db.flush()
        
        # Create user assignments
        ua1 = UserAssignment(
            user_id=1,
            assignment_id=assignment1.id,
            status=AssignmentStatus.IN_PROGRESS,
            hours_done=3.5,
            hours_remaining=6.5,
            last_worked_at=datetime.utcnow() - timedelta(days=1),
            priority=4
        )
        ua2 = UserAssignment(
            user_id=1,
            assignment_id=assignment2.id,
            status=AssignmentStatus.NOT_STARTED,
            hours_done=0.0,
            hours_remaining=4.0,
            priority=5
        )
        ua3 = UserAssignment(
            user_id=1,
            assignment_id=assignment3.id,
            status=AssignmentStatus.NOT_STARTED,
            hours_done=0.0,
            hours_remaining=8.0,
            priority=2
        )
        db.add_all([ua1, ua2, ua3])
        db.flush()
        
        # Create assessment for assignment 1
        assessment1 = AssignmentAssessment(
            assignment_id=assignment1.id,
            version=1,
            is_latest=True,
            effort_hours_low=8.0,
            effort_hours_most=10.0,
            effort_hours_high=14.0,
            difficulty_1to5=3.5,
            weight_in_course=20.0,
            risk_score_0to100=45.0,
            confidence_0to1=0.8,
            milestones=[
                {"label": "Setup environment", "hours": 1.0, "days_before_due": 7},
                {"label": "Implement scraper", "hours": 5.0, "days_before_due": 4},
                {"label": "Testing and docs", "hours": 4.0, "days_before_due": 1}
            ],
            prereq_topics=["HTTP requests", "HTML parsing", "Python basics"],
            deliverables=["Working code", "Documentation", "Test cases"]
        )
        db.add(assessment1)
        db.flush()
        
        # Create study history
        for i in range(5):
            study = StudyHistory(
                user_id=1,
                user_assignment_id=ua1.id,
                date=datetime.utcnow() - timedelta(days=i),
                minutes=60 + (i * 10),
                focus_rating_1to5=4 - (i % 2),
                quality_rating_1to5=4,
                source="ad_hoc",
                notes=f"Study session {i+1}"
            )
            db.add(study)
        
        db.commit()
        
        yield {
            "user_id": 1,
            "course1_id": course1.id,
            "course2_id": course2.id,
            "assignment1_id": assignment1.id,
            "assignment2_id": assignment2.id,
            "assignment3_id": assignment3.id,
        }


@pytest.mark.asyncio
async def test_get_user_assignments_all(setup_test_data):
    """Test retrieving all user assignments."""
    result = await get_user_assignments.ainvoke({"user_id": 1})
    data = json.loads(result)
    
    assert isinstance(data, list)
    assert len(data) == 3
    
    # Check structure
    assignment = data[0]
    assert "assignment_id" in assignment
    assert "title" in assignment
    assert "course" in assignment
    assert "status" in assignment
    assert "hours_done" in assignment
    assert "assessment" in assignment


@pytest.mark.asyncio
async def test_get_user_assignments_filtered_by_status(setup_test_data):
    """Test filtering assignments by status."""
    result = await get_user_assignments.ainvoke({"user_id": 1, "status": "in_progress"})
    data = json.loads(result)
    
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["status"] == "in_progress"
    assert data[0]["title"] == "Python Programming Project"


@pytest.mark.asyncio
async def test_get_user_assignments_filtered_by_course(setup_test_data):
    """Test filtering assignments by course."""
    course_id = setup_test_data["course1_id"]
    result = await get_user_assignments.ainvoke({"user_id": 1, "course_id": course_id})
    data = json.loads(result)
    
    assert isinstance(data, list)
    assert len(data) == 2
    for assignment in data:
        assert assignment["course"]["id"] == course_id


@pytest.mark.asyncio
async def test_get_user_courses(setup_test_data):
    """Test retrieving user's courses."""
    result = await get_user_courses.ainvoke({"user_id": 1})
    data = json.loads(result)
    
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Check structure
    course = data[0]
    assert "course_id" in course
    assert "title" in course
    assert "code" in course
    assert "term" in course
    assert "total_assignments" in course
    assert "active_assignments" in course
    assert "completed_assignments" in course
    
    # Check counts
    cs_course = next(c for c in data if c["code"] == "CS-101")
    assert cs_course["total_assignments"] == 2
    assert cs_course["active_assignments"] == 2


@pytest.mark.asyncio
async def test_get_assignment_assessment(setup_test_data):
    """Test retrieving assignment assessment."""
    assignment_id = setup_test_data["assignment1_id"]
    result = await get_assignment_assessment.ainvoke({"assignment_id": assignment_id, "user_id": 1})
    data = json.loads(result)
    
    assert "assignment_id" in data
    assert data["assignment_id"] == assignment_id
    assert "title" in data
    assert "assessment" in data
    
    assessment = data["assessment"]
    assert "effort_estimates" in assessment
    assert assessment["effort_estimates"]["most_likely_hours"] == 10.0
    assert assessment["difficulty_1to5"] == 3.5
    assert len(assessment["milestones"]) == 3
    assert len(assessment["prerequisites"]) == 3


@pytest.mark.asyncio
async def test_get_assignment_assessment_no_assessment(setup_test_data):
    """Test retrieving assessment for assignment without one."""
    assignment_id = setup_test_data["assignment2_id"]
    result = await get_assignment_assessment.ainvoke({"assignment_id": assignment_id, "user_id": 1})
    data = json.loads(result)
    
    assert data["assignment_id"] == assignment_id
    assert data["assessment"] is None
    assert "message" in data
    assert "No assessment available" in data["message"]


@pytest.mark.asyncio
async def test_get_study_progress(setup_test_data):
    """Test retrieving study progress."""
    result = await get_study_progress.ainvoke({"user_id": 1, "days": 7})
    data = json.loads(result)
    
    assert "user_id" in data
    assert "period_days" in data
    assert "statistics" in data
    assert "recent_sessions" in data
    
    stats = data["statistics"]
    assert stats["total_sessions"] == 5
    assert stats["total_minutes"] == 400  # 60+70+80+90+100
    assert stats["total_hours"] == 6.67  # rounded
    assert stats["average_focus_rating"] is not None
    
    sessions = data["recent_sessions"]
    assert len(sessions) == 5
    assert sessions[0]["assignment"] is not None
    assert sessions[0]["assignment"]["title"] == "Python Programming Project"


@pytest.mark.asyncio
async def test_get_study_progress_filtered_by_assignment(setup_test_data):
    """Test retrieving study progress for specific assignment."""
    assignment_id = setup_test_data["assignment1_id"]
    result = await get_study_progress.ainvoke({"user_id": 1, "assignment_id": assignment_id, "days": 7})
    data = json.loads(result)
    
    assert "filtered_by_assignment_id" in data
    assert data["filtered_by_assignment_id"] == assignment_id
    assert data["statistics"]["total_sessions"] == 5
    
    # All sessions should be for the same assignment
    for session in data["recent_sessions"]:
        assert session["assignment"]["assignment_id"] == assignment_id


@pytest.mark.asyncio
async def test_invalid_status_filter(setup_test_data):
    """Test error handling for invalid status."""
    result = await get_user_assignments.ainvoke({"user_id": 1, "status": "invalid_status"})
    data = json.loads(result)
    
    assert "error" in data
    assert "Invalid status" in data["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
