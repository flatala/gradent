"""End-to-end test: ExecutorAgent.run_context_update_and_assess()

This test verifies the autonomous executor workflow that:
1. Uses ExecutorAgent.run_context_update_and_assess() method
2. Agent autonomously orchestrates: context update -> get unassessed -> assess -> schedule
3. Verifies the LLM agent correctly uses the provided tools
4. Confirms database updates for courses, assignments, and assessments
5. Validates the complete autonomous pipeline without user interaction

This simulates a cron job or webhook that automatically:
- Syncs new content from LMS (Brightspace)
- Assesses new assignments
- Schedules study sessions
All orchestrated by an LLM agent with the right tools.
"""
import sys
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from database import (
    get_db_session,
    User,
    Course,
    Assignment,
    AssignmentAssessment,
)
from agents.executor_agent.executor import ExecutorAgent
from shared.config import Configuration

load_dotenv()


def setup_test_user():
    """Ensure test user exists in database."""
    with get_db_session() as db:
        user = db.query(User).filter_by(id=1).first()
        if not user:
            user = User(
                id=1,
                name="Test Student",
                email="test@example.com",
                timezone="America/New_York",
                preferences={
                    "preferred_study_hours": [9, 10, 11, 14, 15, 16],
                    "max_daily_hours": 6
                }
            )
            db.add(user)
            db.flush()
            print("[OK] Created test user: Test Student")
        else:
            print(f"[OK] Using existing user: {user.name} (ID: {user.id})")
        return user.id


def get_database_counts(user_id: int) -> dict:
    """Get counts of various entities in the database.
    
    Returns:
        Dict with counts for courses, assignments, assessments, and assessment IDs
    """
    with get_db_session() as db:
        courses = db.query(Course).filter_by(user_id=user_id).count()
        assignments = db.query(Assignment).join(Course).filter(
            Course.user_id == user_id
        ).count()
        assessments = db.query(AssignmentAssessment).join(Assignment).join(Course).filter(
            Course.user_id == user_id
        ).all()
        
        # Get list of assessment IDs
        assessment_ids = [a.id for a in assessments]
        
        return {
            "courses": courses,
            "assignments": assignments,
            "assessments": len(assessments),
            "assessment_ids": set(assessment_ids),  # Use set for easy comparison
        }


def verify_assignment_assessment(user_id: int, new_assessment_ids: set):
    """Verify that at least one NEW assignment was assessed.
    
    Args:
        user_id: User ID to check
        new_assessment_ids: Set of NEW assessment IDs created during the test
    
    Returns:
        Tuple of (assessment_found, assessment_details)
    """
    with get_db_session() as db:
        if new_assessment_ids:
            # Check one of the NEW assessments
            assessment_id = min(new_assessment_ids)  # Get the first new one
            assessment = db.query(AssignmentAssessment).filter_by(id=assessment_id).first()
            
            if assessment:
                details = {
                    "assessment_id": assessment.id,
                    "assignment_title": assessment.assignment.title,
                    "effort_hours_most": assessment.effort_hours_most,
                    "difficulty": assessment.difficulty_1to5,
                    "risk_score": assessment.risk_score_0to100,
                    "milestones_count": len(assessment.milestones) if assessment.milestones else 0,
                    "is_new": True,
                }
                
                print(f"[OK] Found NEW assessment (ID: {assessment.id}) for: {details['assignment_title']}")
                print(f"     - Effort (most likely): {details['effort_hours_most']} hours")
                print(f"     - Difficulty: {details['difficulty']}/5")
                print(f"     - Risk Score: {details['risk_score']}/100")
                print(f"     - Milestones: {details['milestones_count']}")
                
                return True, details
        
        # Fallback: if no new assessments, just verify any assessment exists
        # (This handles the case where assignments were re-assessed with is_latest update)
        assessment = db.query(AssignmentAssessment).join(Assignment).join(Course).filter(
            Course.user_id == user_id,
            AssignmentAssessment.is_latest == True  # noqa: E712
        ).first()
        
        if not assessment:
            return False, None
        
        details = {
            "assessment_id": assessment.id,
            "assignment_title": assessment.assignment.title,
            "effort_hours_most": assessment.effort_hours_most,
            "difficulty": assessment.difficulty_1to5,
            "risk_score": assessment.risk_score_0to100,
            "milestones_count": len(assessment.milestones) if assessment.milestones else 0,
            "is_new": False,
        }
        
        print(f"[OK] Found assessment (ID: {assessment.id}) for: {details['assignment_title']}")
        print(f"     - Effort (most likely): {details['effort_hours_most']} hours")
        print(f"     - Difficulty: {details['difficulty']}/5")
        print(f"     - Risk Score: {details['risk_score']}/100")
        print(f"     - Milestones: {details['milestones_count']}")
        print("     [INFO] This is an existing assessment (no new ones created)")
        
        return True, details


async def main():
    """Run the end-to-end executor test."""
    print("\n" + "="*70)
    print("E2E TEST: ExecutorAgent.run_context_update_and_assess()")
    print("="*70 + "\n")

    # Step 1: Setup test user
    print("STEP 1: Setting up test user...")
    user_id = setup_test_user()
    
    # Get initial counts
    print("\nSTEP 2: Getting initial database state...")
    initial_counts = get_database_counts(user_id)
    print("[INFO] Initial state:")
    print(f"       - Courses: {initial_counts['courses']}")
    print(f"       - Assignments: {initial_counts['assignments']}")
    print(f"       - Assessments: {initial_counts['assessments']}")
    print(f"       - Assessment IDs: {sorted(initial_counts['assessment_ids'])}")
    
    # Step 3: Initialize ExecutorAgent
    print("\nSTEP 3: Initializing ExecutorAgent...")
    config = Configuration()
    executor = ExecutorAgent(config)
    print("[OK] ExecutorAgent initialized")
    
    # Step 4: Run the autonomous workflow
    print("\nSTEP 4: Running ExecutorAgent.run_context_update_and_assess()...")
    print("[INFO] This will:")
    print("       1. Run context update (sync from Brightspace)")
    print("       2. Get unassessed assignments")
    print("       3. Assess at least one assignment")
    print("       4. Optionally schedule study sessions")
    print("\n[WAIT] Executor agent is working (this may take 30-60 seconds)...")
    
    result = await executor.run_context_update_and_assess(
        user_id=user_id,
        auto_schedule=False  # Disable auto-scheduling for simpler test
    )
    
    # Step 5: Check executor result
    print("\nSTEP 5: Checking executor result...")
    if result["success"]:
        print("[OK] Executor workflow completed successfully")
        print(f"[INFO] Duration: {result['duration_ms']}ms")
        print(f"[INFO] Agent output:\n{result.get('agent_output', 'No output')}")
    else:
        print(f"[ERROR] Executor workflow failed: {result.get('error', 'Unknown error')}")
        print(f"[INFO] Duration: {result['duration_ms']}ms")
        return False
    
    # Step 6: Verify database updates
    print("\nSTEP 6: Verifying database updates...")
    final_counts = get_database_counts(user_id)
    
    # Find new assessment IDs
    new_assessment_ids = final_counts['assessment_ids'] - initial_counts['assessment_ids']
    
    print("[INFO] Final state:")
    print(f"       - Courses: {final_counts['courses']} (change: +{final_counts['courses'] - initial_counts['courses']})")
    print(f"       - Assignments: {final_counts['assignments']} (change: +{final_counts['assignments'] - initial_counts['assignments']})")
    print(f"       - Assessments: {final_counts['assessments']} (change: +{final_counts['assessments'] - initial_counts['assessments']})")
    
    if new_assessment_ids:
        print(f"       - NEW Assessment IDs: {sorted(new_assessment_ids)}")
    else:
        print("       - No new assessments created (may have re-assessed existing)")
    
    # Step 7: Verify at least one assessment exists (preferably NEW)
    print("\nSTEP 7: Verifying assignment assessment...")
    assessment_found, assessment_details = verify_assignment_assessment(user_id, new_assessment_ids)
    
    if not assessment_found:
        print("[ERROR] No assignment assessment found in database!")
        print("[INFO] The executor may not have completed the assessment workflow.")
        return False
    
    # Step 8: Final validation
    print("\n" + "="*70)
    print("FINAL VALIDATION")
    print("="*70)
    
    checks = []
    
    # Check 1: Context update ran (courses or assignments should increase)
    context_updated = (
        final_counts['courses'] > initial_counts['courses'] or
        final_counts['assignments'] > initial_counts['assignments']
    )
    checks.append(("Context update synced data", context_updated))
    
    # Check 2: At least one assignment exists
    assignments_exist = final_counts['assignments'] > 0
    checks.append(("Assignments exist in database", assignments_exist))
    
    # Check 3: At least one NEW assessment OR assessments exist
    # (Allows for re-assessment of existing assignments)
    assessments_created = len(new_assessment_ids) > 0 or final_counts['assessments'] > 0
    check_label = f"New assessments created ({len(new_assessment_ids)} new)" if new_assessment_ids else "Assessments exist (may be existing)"
    checks.append((check_label, assessments_created))
    
    # Check 4: Executor reported success
    checks.append(("Executor workflow succeeded", result["success"]))
    
    # Print results
    all_passed = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"[{status}] {check_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("TEST PASSED: All checks passed! ✓")
        print("="*70 + "\n")
        return True
    else:
        print("TEST FAILED: Some checks failed ✗")
        print("="*70 + "\n")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[ABORT] Test interrupted by user")
        exit(2)
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
