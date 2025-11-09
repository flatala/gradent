"""Quick test script for ExecutorAgent.

This demonstrates autonomous task execution without user interaction.

Usage:
    poetry run python test_executor.py
"""
import asyncio
from datetime import datetime, timedelta
from agents.executor_agent import ExecutorAgent
from shared.config import Configuration


async def main():
    """Test ExecutorAgent.execute_schedule_meeting()"""

    print("=" * 60)
    print("ExecutorAgent Test - Autonomous Meeting Scheduling")
    print("=" * 60)

    # Initialize executor
    config = Configuration()
    executor = ExecutorAgent(config)

    # Calculate a time tomorrow at 2pm
    tomorrow_2pm = (datetime.now() + timedelta(days=1)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )

    print(f"\n📅 Scheduling test meeting for {tomorrow_2pm.isoformat()}")
    print("   (This is an autonomous operation - no user interaction)\n")

    # Execute autonomous scheduling
    result = await executor.execute_schedule_meeting(
        meeting_name="ExecutorAgent Test Meeting",
        duration_minutes=30,
        preferred_time=tomorrow_2pm.isoformat(),
        topic="Testing autonomous execution",
        location="Google Meet"
    )

    # Display results
    print("\n" + "=" * 60)
    if result["success"]:
        print("✓ SUCCESS - Meeting scheduled autonomously!")
        print(f"  Event ID: {result['event_id']}")
        print(f"  Title: {result['title']}")
        print(f"  Time: {result['start_time']} → {result['end_time']}")
        print(f"  Calendar: {result['calendar_link']}")
        if result.get('meeting_link'):
            print(f"  Google Meet: {result['meeting_link']}")
        print(f"  Duration: {result['duration_ms']}ms")
    else:
        print("✗ FAILED - Could not schedule meeting")
        print(f"  Error: {result['error']}")
        print(f"  Duration: {result['duration_ms']}ms")
    print("=" * 60)

    print("\n💡 Key Points:")
    print("  - ExecutorAgent runs autonomously (no user chat)")
    print("  - Returns structured results (dict, not conversation)")
    print("  - Designed for cron jobs / webhooks / event triggers")
    print("  - MainAgent (chat) remains unchanged\n")


if __name__ == "__main__":
    asyncio.run(main())
