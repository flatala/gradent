#!/usr/bin/env python3
"""Quick test script for ntfy.sh notifications."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from notifications.autonomous import send_ntfy_notification


async def main():
    """Test ntfy notification."""
    print("🧪 Testing ntfy.sh notification...")
    print("=" * 60)
    
    # Use a test topic
    topic = "gradent-ai-test-123"
    
    print(f"\n📱 Subscribe to receive this notification:")
    print(f"   Web: https://ntfy.sh/{topic}")
    print(f"   Mobile: Open ntfy app and add topic '{topic}'")
    print("\n⏳ Sending test notification in 3 seconds...")
    print("=" * 60)
    
    await asyncio.sleep(3)
    
    success = await send_ntfy_notification(
        message="🎉 Success! Your ntfy integration is working!\n\nThis is a test from GradEnt AI.",
        topic=topic,
        title="✅ Test Notification",
        priority=5,
        tags=["tada", "robot", "white_check_mark"]
    )
    
    if success:
        print("\n✅ Notification sent successfully!")
        print(f"\n📱 Check your subscription at: https://ntfy.sh/{topic}")
        print("\nIf you didn't see it:")
        print(f"1. Open https://ntfy.sh/{topic} in your browser")
        print(f"2. Or download the ntfy mobile app and subscribe to '{topic}'")
    else:
        print("\n❌ Failed to send notification")
        print("Check your internet connection or try again")
    
    print("\n" + "=" * 60)
    

if __name__ == "__main__":
    asyncio.run(main())

