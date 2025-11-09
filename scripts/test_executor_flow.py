"""Test script for the executor agent's context update and assess flow.

This demonstrates the new autonomous workflow:
1. Context Update: Sync from Brightspace
2. Change Detection: Find new/updated assignments
3. Auto Assessment: Assess new assignments
4. Auto Scheduling: Schedule study sessions
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path so we can import from root modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import Configuration
from agents.executor_agent import ExecutorAgent


async def test_context_update_flow():
    """Test the context update, assessment, and scheduling flow."""
    print("\n" + "=" * 70)
    print("Testing Executor Agent: Context Update → Assessment → Scheduling")
    print("=" * 70 + "\n")

    # Initialize configuration and executor
    config = Configuration()
    executor = ExecutorAgent(config)

    # Run the flow for user_id=1
    print("Starting autonomous workflow for user_id=1...")
    print("This will:")
    print("  1. Sync courses and assignments from Brightspace")
    print("  2. Detect new assignments without assessments")
    print("  3. Run AI assessment on each new assignment")
    print("  4. Schedule study sessions based on effort estimates\n")

    result = await executor.run_context_update_and_assess(
        user_id=1,
        auto_schedule=True  # Set to False to skip auto-scheduling
    )

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70 + "\n")

    print(f"Success: {result['success']}")
    print(f"Duration: {result['duration_ms']}ms\n")

    if result.get('error'):
        print(f"Error: {result['error']}\n")
        return

    # Context update stats
    print("Context Update:")
    ctx = result.get('context_update', {})
    print(f"  Courses synced: {ctx.get('courses_synced', 0)}")
    print(f"  Assignments synced: {ctx.get('assignments_synced', 0)}")
    print(f"  Content chunks indexed: {ctx.get('content_indexed', 0)}\n")

    # Assessments
    assessments = result.get('assessments', [])
    print(f"Assessments: {len(assessments)} assignment(s) assessed")
    for assessment in assessments:
        print(f"\n  Assignment: {assessment['title']}")
        print(f"    Effort: {assessment['effort_hours']:.1f} hours")
        print(f"    Difficulty: {assessment['difficulty']:.1f}/5")
        print(f"    Risk Score: {assessment['risk_score']:.0f}/100")
        print(f"    Milestones: {len(assessment.get('milestones', []))}")

    # Scheduled sessions
    sessions = result.get('scheduled_sessions', [])
    print(f"\nScheduled Sessions: {len(sessions)} session(s) created")
    for session in sessions:
        print(f"\n  {session['assignment']}")
        print(f"    Session: {session['session']}")
        print(f"    Start: {session['start_time']}")
        print(f"    Duration: {session['duration_minutes']} min")
        print(f"    Event ID: {session['event_id']}")

    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_context_update_flow())
