"""Generate mock data for testing the database."""
from datetime import datetime, timedelta
from typing import List

from .connection import get_db_session, init_db
from .models import User, Course, Assignment, AssignmentAssessment, AssignmentStatus


def create_mock_user() -> int:
    """Create a mock user and return the user ID."""
    with get_db_session() as db:
        user = User(
            name="Alex Student",
            email="alex@example.com",
            timezone="America/New_York",
            preferences={
                "preferred_study_hours": [9, 10, 11, 14, 15, 16, 19, 20],
                "max_daily_hours": 6,
                "break_frequency_minutes": 50,
                "notification_preferences": {"email": True, "push": False}
            }
        )
        db.add(user)
        db.flush()
        user_id = user.id
        print(f"[OK] Created user: {user.name} (ID: {user_id})")
        return user_id


def create_mock_courses(user_id: int) -> List[int]:
    """Create mock courses and return course IDs."""
    with get_db_session() as db:
        courses = [
            Course(
                user_id=user_id,
                title="Reinforcement Learning",
                code="CS-7642",
                term="Fall 2024",
                lms_course_id="brightspace_12345"
            ),
            Course(
                user_id=user_id,
                title="Machine Learning",
                code="CS-7641",
                term="Fall 2024",
                lms_course_id="brightspace_12346"
            ),
            Course(
                user_id=user_id,
                title="Computer Vision",
                code="CS-6476",
                term="Fall 2024",
                lms_course_id="brightspace_12347"
            ),
        ]
        db.add_all(courses)
        db.flush()
        course_ids = [c.id for c in courses]
        print(f"[OK] Created {len(courses)} courses")
        return course_ids


def create_mock_assignments(course_ids: List[int]) -> List[int]:
    """Create mock assignments and return assignment IDs."""
    with get_db_session() as db:
        now = datetime.now()
        
        assignments = [
            # RL Course assignments
            Assignment(
                course_id=course_ids[0],
                title="Markov Decision Processes - Implementation",
                description_short="Implement value iteration and policy iteration for gridworld MDPs",
                due_at=now + timedelta(days=14),
                lms_link="https://brightspace.gatech.edu/assignment/1",
                status=AssignmentStatus.NOT_STARTED
            ),
            Assignment(
                course_id=course_ids[0],
                title="Q-Learning and Deep RL Project",
                description_short="Train a DQN agent on Atari games and analyze performance",
                due_at=now + timedelta(days=28),
                lms_link="https://brightspace.gatech.edu/assignment/2",
                status=AssignmentStatus.NOT_STARTED
            ),
            # ML Course assignments
            Assignment(
                course_id=course_ids[1],
                title="Supervised Learning Analysis",
                description_short="Compare decision trees, neural nets, boosting, SVM, and kNN on two datasets",
                due_at=now + timedelta(days=21),
                lms_link="https://brightspace.gatech.edu/assignment/3",
                status=AssignmentStatus.IN_PROGRESS,
                estimated_hours_user=15.0
            ),
            Assignment(
                course_id=course_ids[1],
                title="Randomized Optimization",
                description_short="Implement and analyze genetic algorithms, simulated annealing, and MIMIC",
                due_at=now + timedelta(days=35),
                lms_link="https://brightspace.gatech.edu/assignment/4",
                status=AssignmentStatus.NOT_STARTED
            ),
            # CV Course assignments
            Assignment(
                course_id=course_ids[2],
                title="Image Filtering and Hybrid Images",
                description_short="Implement Gaussian and Laplacian pyramids, create hybrid images",
                due_at=now + timedelta(days=10),
                lms_link="https://brightspace.gatech.edu/assignment/5",
                status=AssignmentStatus.IN_PROGRESS,
                estimated_hours_user=8.0
            ),
        ]
        
        db.add_all(assignments)
        db.flush()
        assignment_ids = [a.id for a in assignments]
        print(f"[OK] Created {len(assignments)} assignments")
        return assignment_ids


def create_mock_assessments(assignment_ids: List[int]) -> None:
    """Create mock AI assessments for assignments."""
    with get_db_session() as db:
        assessments = [
            # MDP Implementation assessment
            AssignmentAssessment(
                assignment_id=assignment_ids[0],
                version=1,
                is_latest=True,
                effort_hours_low=8.0,
                effort_hours_most=12.0,
                effort_hours_high=16.0,
                difficulty_1to5=3.5,
                weight_in_course=15.0,
                risk_score_0to100=45.0,
                confidence_0to1=0.85,
                milestones=[
                    {"label": "Read MDP chapter and understand notation", "hours": 2.0, "days_before_due": 12},
                    {"label": "Implement value iteration", "hours": 4.0, "days_before_due": 9},
                    {"label": "Implement policy iteration", "hours": 3.0, "days_before_due": 6},
                    {"label": "Test and debug", "hours": 2.0, "days_before_due": 3},
                    {"label": "Write report", "hours": 1.0, "days_before_due": 1},
                ],
                prereq_topics=["Markov chains", "Dynamic programming", "Bellman equations"],
                deliverables=["Python code", "Report PDF", "Test results"],
                blocking_dependencies=[],
                sources=[{"type": "assignment_pdf", "doc_id": "assignment_1_pdf"}],
                model_meta={"model": "gpt-4o", "timestamp": datetime.now().isoformat()}
            ),
            # Q-Learning assessment
            AssignmentAssessment(
                assignment_id=assignment_ids[1],
                version=1,
                is_latest=True,
                effort_hours_low=20.0,
                effort_hours_most=30.0,
                effort_hours_high=40.0,
                difficulty_1to5=4.5,
                weight_in_course=25.0,
                risk_score_0to100=75.0,
                confidence_0to1=0.78,
                milestones=[
                    {"label": "Set up OpenAI Gym environment", "hours": 3.0, "days_before_due": 25},
                    {"label": "Implement Q-learning algorithm", "hours": 5.0, "days_before_due": 21},
                    {"label": "Build DQN architecture", "hours": 8.0, "days_before_due": 16},
                    {"label": "Train and tune hyperparameters", "hours": 8.0, "days_before_due": 10},
                    {"label": "Run experiments and collect metrics", "hours": 4.0, "days_before_due": 5},
                    {"label": "Write comprehensive report", "hours": 2.0, "days_before_due": 2},
                ],
                prereq_topics=["Q-learning", "Neural networks", "PyTorch/TensorFlow", "Atari preprocessing"],
                deliverables=["Source code", "Trained models", "Performance plots", "Analysis report"],
                blocking_dependencies=["GPU access for training"],
                sources=[{"type": "assignment_pdf", "doc_id": "assignment_2_pdf"}],
                model_meta={"model": "gpt-4o", "timestamp": datetime.now().isoformat()}
            ),
            # Supervised Learning assessment
            AssignmentAssessment(
                assignment_id=assignment_ids[2],
                version=1,
                is_latest=True,
                effort_hours_low=12.0,
                effort_hours_most=18.0,
                effort_hours_high=24.0,
                difficulty_1to5=3.0,
                weight_in_course=20.0,
                risk_score_0to100=40.0,
                confidence_0to1=0.90,
                milestones=[
                    {"label": "Dataset selection and preprocessing", "hours": 3.0, "days_before_due": 18},
                    {"label": "Implement decision trees and neural nets", "hours": 5.0, "days_before_due": 14},
                    {"label": "Implement boosting, SVM, kNN", "hours": 5.0, "days_before_due": 10},
                    {"label": "Run experiments and cross-validation", "hours": 3.0, "days_before_due": 6},
                    {"label": "Analyze results and write report", "hours": 2.0, "days_before_due": 2},
                ],
                prereq_topics=["Supervised learning basics", "Scikit-learn", "Cross-validation", "Model evaluation"],
                deliverables=["Analysis code", "Experimental results", "Comparison report"],
                blocking_dependencies=[],
                sources=[{"type": "assignment_pdf", "doc_id": "assignment_3_pdf"}],
                model_meta={"model": "gpt-4o", "timestamp": datetime.now().isoformat()}
            ),
            # Image Filtering assessment
            AssignmentAssessment(
                assignment_id=assignment_ids[4],
                version=1,
                is_latest=True,
                effort_hours_low=6.0,
                effort_hours_most=10.0,
                effort_hours_high=14.0,
                difficulty_1to5=2.5,
                weight_in_course=10.0,
                risk_score_0to100=30.0,
                confidence_0to1=0.88,
                milestones=[
                    {"label": "Review filtering theory", "hours": 1.5, "days_before_due": 8},
                    {"label": "Implement Gaussian pyramid", "hours": 2.5, "days_before_due": 6},
                    {"label": "Implement Laplacian pyramid", "hours": 2.5, "days_before_due": 4},
                    {"label": "Create hybrid images", "hours": 2.5, "days_before_due": 2},
                    {"label": "Testing and documentation", "hours": 1.0, "days_before_due": 1},
                ],
                prereq_topics=["Convolution", "Frequency domain", "Image pyramids"],
                deliverables=["Python implementation", "Hybrid image results", "Brief report"],
                blocking_dependencies=[],
                sources=[{"type": "lecture_slides", "doc_id": "cv_lecture_3"}],
                model_meta={"model": "gpt-4o-mini", "timestamp": datetime.now().isoformat()}
            ),
        ]
        
        db.add_all(assessments)
        db.flush()
        print(f"[OK] Created {len(assessments)} assignment assessments")


def populate_mock_data() -> None:
    """Populate the database with complete mock data."""
    print("\n" + "=" * 60)
    print("Populating database with mock data...")
    print("=" * 60 + "\n")
    
    # Ensure database exists
    init_db()
    
    # Create data in order
    user_id = create_mock_user()
    course_ids = create_mock_courses(user_id)
    assignment_ids = create_mock_assignments(course_ids)
    create_mock_assessments(assignment_ids)
    
    print("\n" + "=" * 60)
    print("[OK] Mock data population complete!")
    print("=" * 60)
    print(f"\nDatabase location: {get_db_session}")
    print("\nYou can now query the database to verify the data.")


def clear_all_data() -> None:
    """Clear all data from the database (for testing)."""
    from .models import Base
    from .connection import engine
    
    print("\n[WARN]  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("[OK] All tables dropped")
    
    print("Recreating tables...")
    init_db()


if __name__ == "__main__":
    # Can be run directly to populate data
    clear_all_data()
    populate_mock_data()
