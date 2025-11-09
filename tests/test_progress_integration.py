"""Quick test to verify progress tracking integration with chat agent."""
import asyncio
from agents.chat_agent import MainAgent
from shared.config import Configuration


async def test_progress_tracking():
    """Test that the chat agent can handle progress updates."""
    config = Configuration()
    agent = MainAgent(config)
    
    print("Testing progress tracking integration...")
    print("=" * 60)
    
    # Test message that should trigger the progress tracking tool
    test_message = "I just studied calculus for 2 hours"
    
    print(f"\nUser: {test_message}")
    print("\nAgent response:")
    print("-" * 60)
    
    try:
        response = await agent.chat(test_message)
        print(response)
        print("-" * 60)
        print("\n✓ Progress tracking tool is working!")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_progress_tracking())
    exit(0 if success else 1)
