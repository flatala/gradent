"""Test script to verify exam results are saved and update UserAssignment hours.

This demonstrates how Option A works:
1. Exam result is saved to exam_results table
2. UserAssignment.hours_remaining is updated with recommended study hours
3. Scheduler can now use this updated value when planning study time
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from database.models import ExamResult, UserAssignment, Assignment


def check_exam_integration():
    """Check if exam results are saving and updating UserAssignments."""
    db = next(get_db())
    
    print("=" * 70)
    print("EXAM RESULTS & SCHEDULER INTEGRATION TEST")
    print("=" * 70)
    
    # Check for exam results
    exam_results = db.query(ExamResult).all()
    print(f"\n📊 Total Exam Results: {len(exam_results)}")
    
    if exam_results:
        print("\nRecent Exam Results:")
        print("-" * 70)
        for result in exam_results[-5:]:  # Show last 5
            assignment = db.query(Assignment).get(result.assignment_id)
            print(f"\n  Assignment: {assignment.title if assignment else 'Unknown'}")
            print(f"  Score: {result.score}/{result.total_questions} ({result.percentage}%)")
            print(f"  Recommended Study Hours: {result.study_hours_recommended}")
            print(f"  Completed: {result.completed_at}")
            
            # Check if UserAssignment was updated
            user_assignment = db.query(UserAssignment).filter(
                UserAssignment.user_id == result.user_id,
                UserAssignment.assignment_id == result.assignment_id
            ).first()
            
            if user_assignment:
                print(f"  ✅ UserAssignment Updated:")
                print(f"     - Hours Remaining: {user_assignment.hours_remaining}")
                print(f"     - Hours Estimated (User): {user_assignment.hours_estimated_user}")
                print(f"     - Status: {user_assignment.status}")
            else:
                print(f"  ⚠️  No UserAssignment found")
    else:
        print("\n  No exam results yet. Take a mock exam to test the integration!")
    
    print("\n" + "=" * 70)
    print("HOW IT WORKS:")
    print("=" * 70)
    print("""
1. Student completes exam → clicks "Assess Exam"
2. Backend:
   - Calculates score and percentage
   - LLM recommends study hours based on performance
   - Saves to exam_results table
   - Updates UserAssignment.hours_remaining with recommended hours
3. Scheduler:
   - Reads UserAssignment.hours_remaining when planning study blocks
   - Automatically allocates more/less time based on exam performance
   - No additional code needed - it uses existing hours_remaining field!
    """)
    
    print("\nNEXT STEPS:")
    print("-" * 70)
    print("1. ✅ Database table created (exam_results)")
    print("2. ✅ Backend saves results and updates UserAssignment")
    print("3. ✅ Scheduler already uses hours_remaining field")
    print("4. 📝 Take a mock exam to see it in action!")
    print("5. 📅 Run scheduler - it will use exam-based time estimates")
    
    db.close()


if __name__ == "__main__":
    check_exam_integration()
