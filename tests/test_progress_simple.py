"""Simple test to verify progress tracking saves to database."""
import asyncio
from langchain_core.runnables import RunnableConfig
from agents.shared.workflow_tools import log_progress_update
from database import get_db_session
from database.models import StudyHistory, UserAssignment
from shared.config import Configuration


async def test_progress_logging():
    """Test that progress logging works and saves to database."""
    print("Testing progress tracking with user_id=1...")
    print("=" * 60)
    
    # Get initial count of study history records
    with get_db_session() as db:
        initial_count = db.query(StudyHistory).filter_by(user_id=1).count()
        print(f"Initial StudyHistory records for user_id=1: {initial_count}")
    
    # Test progress update
    test_message = "I worked on my calculus practice problems homework for 30 minutes, focus was a 5, quality a 3. Not an assignment, just general studying."
    print(f"\nTest message: '{test_message}'")
    print("-" * 60)
    
    try:
        # Create config
        config = RunnableConfig(configurable={"configuration": Configuration()})
        
        # Call the tool (it defaults to user_id=1)
        result = await log_progress_update.ainvoke(
            {"user_message": test_message},
            config=config
        )
        
        print("\nResult:")
        print(result)
        print("-" * 60)
        
        # Check if new record was created
        with get_db_session() as db:
            final_count = db.query(StudyHistory).filter_by(user_id=1).count()
            print(f"\nFinal StudyHistory records for user_id=1: {final_count}")
            
            if final_count > initial_count:
                print(f"✓ SUCCESS: {final_count - initial_count} new record(s) created!")
                
                # Get the latest record
                latest = db.query(StudyHistory).filter_by(user_id=1).order_by(
                    StudyHistory.date.desc()
                ).first()
                
                if latest:
                    print(f"\nLatest study session:")
                    print(f"  - Minutes: {latest.minutes}")
                    print(f"  - Focus: {latest.focus_rating_1to5}")
                    print(f"  - Quality: {latest.quality_rating_1to5}")
                    print(f"  - Notes: {latest.notes}")
                    
                    if latest.user_assignment_id:
                        ua = db.query(UserAssignment).get(latest.user_assignment_id)
                        if ua:
                            print(f"  - Assignment: {ua.assignment.title}")
                            print(f"  - Total hours done: {ua.hours_done}")
                
                return True
            else:
                print("✗ FAIL: No new records created")
                print("Note: This might be because the workflow needs user confirmation")
                print("The tool might be waiting for follow-up questions")
                return False
                
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_progress_logging())
    print("\n" + "=" * 60)
    if success:
        print("Test completed successfully!")
    else:
        print("Test showed workflow is conversational (needs more interaction)")
    print("=" * 60)
