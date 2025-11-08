"""Test script for assignment assessment workflow and database.

This script demonstrates:
1. Database setup and initialization
2. Creating mock data
3. Running the assignment assessment workflow
4. Querying the results
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    init_db,
    get_db_session,
    User,
    Course,
    Assignment,
    AssignmentAssessment,
    AssignmentStatus,
)
from database import mock_data
from workflows.assignment_assessment import AssignmentInfo, AssessmentState, assessment_graph
from shared.config import Configuration


async def test_assessment_workflow():
    """Test the assignment assessment workflow with a sample assignment."""
    print("\n" + "=" * 60)
    print("Testing Assignment Assessment Workflow")
    print("=" * 60 + "\n")
    
    # Initialize configuration
    config = Configuration()
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please set OPENAI_API_KEY in your .env file")
        return
    
    # Create a test assignment to assess
    assignment_info = AssignmentInfo(
        title="Build a Convolutional Neural Network",
        description="""
        Implement a CNN from scratch using NumPy for image classification.
        
        Requirements:
        - Implement convolution, pooling, and fully connected layers
        - Support forward and backward propagation
        - Train on CIFAR-10 dataset
        - Achieve at least 60% accuracy
        - Write a 3-page report analyzing your architecture choices
        
        Deliverables:
        - Python code with documentation
        - Trained model weights
        - Training curves (loss/accuracy)
        - Written report (PDF)
        
        Due: 2 weeks from today
        Worth: 20% of final grade
        """,
        course_name="Deep Learning",
        due_date=datetime.now() + timedelta(days=14),
    )
    
    # Create initial state
    initial_state = AssessmentState(
        assignment_info=assignment_info,
        user_id=1,
    )
    
    print("Running assessment workflow...\n")
    
    # Run the workflow
    try:
        result = await assessment_graph.ainvoke(
            initial_state,
            config={"configurable": config.__dict__}
        )
        
        # Display results
        assessment = result.get("assessment")
        if assessment:
            print("\n" + "=" * 60)
            print("Assessment Results")
            print("=" * 60 + "\n")
            
            print(f"Assignment: {assignment_info.title}")
            print(f"Course: {assignment_info.course_name}\n")
            
            print(f"Effort Estimates:")
            print(f"  Optimistic:   {assessment.effort_hours_low:.1f} hours")
            print(f"  Most Likely:  {assessment.effort_hours_most:.1f} hours")
            print(f"  Pessimistic:  {assessment.effort_hours_high:.1f} hours")
            
            print(f"\nDifficulty: {assessment.difficulty_1to5:.1f}/5.0")
            print(f"Risk Score: {assessment.risk_score_0to100:.0f}/100")
            print(f"Confidence: {assessment.confidence_0to1:.0%}\n")
            
            if assessment.milestones:
                print("Milestones:")
                for i, milestone in enumerate(assessment.milestones, 1):
                    print(f"  {i}. {milestone.get('label')} ({milestone.get('hours', 0):.1f}h, "
                          f"{milestone.get('days_before_due', 0)} days before due)")
            
            if assessment.prereq_topics:
                print(f"\nPrerequisites: {', '.join(assessment.prereq_topics)}")
            
            if assessment.deliverables:
                print(f"\nDeliverables: {', '.join(assessment.deliverables)}")
            
            if assessment.blocking_dependencies:
                print(f"\nBlockers: {', '.join(assessment.blocking_dependencies)}")
            
            print(f"\nSummary: {assessment.summary}")
            
            if result.get("assessment_record_id"):
                print(f"\n[OK] Assessment saved to database (ID: {result['assessment_record_id']})")
            
        else:
            print("❌ No assessment generated")
            
    except Exception as e:
        print(f"❌ Error running workflow: {e}")
        import traceback
        traceback.print_exc()


def query_database():
    """Query and display database contents."""
    print("\n" + "=" * 60)
    print("Database Contents")
    print("=" * 60 + "\n")
    
    with get_db_session() as db:
        # Count records
        user_count = db.query(User).count()
        course_count = db.query(Course).count()
        assignment_count = db.query(Assignment).count()
        assessment_count = db.query(AssignmentAssessment).count()
        
        print(f"Users: {user_count}")
        print(f"Courses: {course_count}")
        print(f"Assignments: {assignment_count}")
        print(f"Assessments: {assessment_count}\n")
        
        # Show assignments with their latest assessments
        if assignment_count > 0:
            print("Assignments with Assessments:")
            print("-" * 60)
            
            assignments = db.query(Assignment).join(Course).all()
            for assignment in assignments:
                latest_assessment = db.query(AssignmentAssessment).filter(
                    AssignmentAssessment.assignment_id == assignment.id,
                    AssignmentAssessment.is_latest == True
                ).first()
                
                print(f"\n{assignment.title}")
                print(f"  Course: {assignment.course.title}")
                print(f"  Status: {assignment.status.value}")
                if assignment.due_at:
                    days_until = (assignment.due_at - datetime.now()).days
                    print(f"  Due: {assignment.due_at.strftime('%Y-%m-%d')} ({days_until} days)")
                
                if latest_assessment:
                    print(f"  Effort: {latest_assessment.effort_hours_most:.1f}h "
                          f"({latest_assessment.effort_hours_low:.1f}-{latest_assessment.effort_hours_high:.1f}h)")
                    print(f"  Difficulty: {latest_assessment.difficulty_1to5:.1f}/5")
                    print(f"  Risk: {latest_assessment.risk_score_0to100:.0f}/100")
                    print(f"  Milestones: {len(latest_assessment.milestones or [])}")
                else:
                    print("  No assessment yet")


def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("Assignment Assessment & Database Test")
    print("=" * 60)
    
    # Setup database
    print("\nStep 1: Initialize database...")
    mock_data.clear_all_data()
    mock_data.populate_mock_data()
    
    # Query initial state
    print("\nStep 2: Query initial database state...")
    query_database()
    
    # Test workflow
    print("\nStep 3: Test assignment assessment workflow...")
    asyncio.run(test_assessment_workflow())
    
    # Show final state
    print("\nStep 4: Query final database state...")
    query_database()
    
    print("\n" + "=" * 60)
    print("[OK] Test completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
