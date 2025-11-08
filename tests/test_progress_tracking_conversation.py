"""
Demo/test for the conversational progress tracking workflow.

This shows how the workflow handles natural language input and asks
follow-up questions when information is missing.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
load_dotenv(project_root / ".env")

# Verify API key is loaded
if not os.getenv("OPENAI_API_KEY"):
    print("\n" + "="*70)
    print("⚠️  OPENAI_API_KEY NOT FOUND")
    print("="*70)
    print("\nThis test requires an OpenAI API key to make LLM calls.")
    print("\nOption 1: Create a .env file in the project root:")
    print(f"  {project_root / '.env'}")
    print("\n  Content:")
    print("  OPENAI_API_KEY=sk-your-key-here")
    print("\nOption 2: Set environment variable:")
    print("  export OPENAI_API_KEY=sk-your-key-here")
    print("\nOption 3: Copy .env.example to .env and add your key:")
    print(f"  cp {project_root / '.env.example'} {project_root / '.env'}")
    print("\n" + "="*70 + "\n")
    sys.exit(1)

print(f"[OK] OpenAI API key loaded (starts with: {os.getenv('OPENAI_API_KEY')[:10]}...)\n")

from database import init_db, get_db_session
from database.models import User, Course, Assignment, UserAssignment
from workflows.progress_tracking import run_progress_tracking
from datetime import datetime, timedelta


def setup_test_user():
    """Create a test user with some assignments."""
    print("Setting up test data...")
    
    with get_db_session() as session:
        # Check if test user already exists
        user = session.query(User).filter_by(email="demo@example.com").first()
        
        if not user:
            # Create test user
            user = User(
                name="Demo Student",
                email="demo@example.com"
            )
            session.add(user)
            session.flush()
            
            # Create test course
            course = Course(
                user_id=user.id,
                title="AI & Machine Learning",
                code="AI101",
                lms_course_id="ai_ml_101"
            )
            session.add(course)
            session.flush()
            
            # Create test assignments
            assignments = [
                ("Reinforcement Learning Project", "Implement Q-learning and DQN", 10.0),
                ("Assignment 2: ML Basics", "Linear regression and gradient descent", 8.0),
                ("Neural Networks Lab", "Build a CNN for image classification", 12.0),
            ]
            
            for name, instructions, hours in assignments:
                assignment = Assignment(
                    course_id=course.id,
                    title=name,
                    description_short=instructions,
                    due_at=datetime.now() + timedelta(days=14),
                    lms_assignment_id=f"assign_{name.lower().replace(' ', '_')}",
                    weight_percentage=30.0
                )
                session.add(assignment)
                session.flush()
                
                # Create UserAssignment
                ua = UserAssignment(
                    user_id=user.id,
                    assignment_id=assignment.id,
                    status="NOT_STARTED",
                    hours_done=0.0,
                    hours_remaining=hours
                )
                session.add(ua)
            
            session.commit()
            print(f"Created demo user (ID: {user.id}) with 3 assignments\n")
        else:
            print(f"Using existing demo user (ID: {user.id})\n")
        
        return user.id


def simulate_conversation(user_id: int, conversation: list[str]):
    """Simulate a multi-turn conversation.
    
    Args:
        user_id: User ID
        conversation: List of user messages to simulate
    """
    print("=" * 70)
    print("CONVERSATION SIMULATION")
    print("=" * 70)
    
    state = None
    
    for i, user_message in enumerate(conversation):
        print(f"\n{'User:':<10} {user_message}")
        
        result = run_progress_tracking(
            user_id=user_id,
            user_message=user_message,
            conversation_state=state
        )
        
        print(f"{'Assistant:':<10} {result['response']}")
        
        # Update state for next turn
        state = result["state"]
        
        # Check if conversation is done
        if result["done"]:
            if result["success"]:
                print(f"\n{'='*70}")
                print("✅ Progress logged successfully!")
                print(f"{'='*70}")
                if result.get("logged_data"):
                    data = result["logged_data"]
                    print(f"Logged data: {data}")
            else:
                print(f"\n{'='*70}")
                print("❌ Conversation ended without logging")
                print(f"{'='*70}")
            break
    
    print("\n")


def demo_scenario_1():
    """Scenario 1: User provides complete information upfront."""
    print("\n" + "="*70)
    print("SCENARIO 1: Complete Information Upfront")
    print("="*70)
    print("User provides assignment, duration, and quality indicators immediately\n")
    
    user_id = setup_test_user()
    
    conversation = [
        "I worked on the RL project for 90 minutes and was really focused, made good progress!",
        "yes"  # Confirm
    ]
    
    simulate_conversation(user_id, conversation)


def demo_scenario_2():
    """Scenario 2: Missing duration, system asks follow-up."""
    print("\n" + "="*70)
    print("SCENARIO 2: Missing Duration")
    print("="*70)
    print("User mentions assignment but not how long they studied\n")
    
    user_id = setup_test_user()
    
    conversation = [
        "I just finished studying the neural networks lab",
        "About 2 hours",
        "yes"  # Confirm
    ]
    
    simulate_conversation(user_id, conversation)


def demo_scenario_3():
    """Scenario 3: Vague assignment reference, system clarifies."""
    print("\n" + "="*70)
    print("SCENARIO 3: Vague Assignment Reference")
    print("="*70)
    print("User says 'assignment 2' which needs clarification\n")
    
    user_id = setup_test_user()
    
    conversation = [
        "I studied assignment 2 for 60 minutes",
        "The ML basics one",
        "yes"  # Confirm
    ]
    
    simulate_conversation(user_id, conversation)


def demo_scenario_4():
    """Scenario 4: Very vague, multiple follow-ups needed."""
    print("\n" + "="*70)
    print("SCENARIO 4: Very Vague - Multiple Follow-ups")
    print("="*70)
    print("User provides minimal info, system asks multiple questions\n")
    
    user_id = setup_test_user()
    
    conversation = [
        "I just finished studying",
        "The RL project",
        "About 45 minutes",
        "Pretty focused, maybe 4 out of 5",
        "yes"  # Confirm
    ]
    
    simulate_conversation(user_id, conversation)


def demo_scenario_5():
    """Scenario 5: User cancels mid-conversation."""
    print("\n" + "="*70)
    print("SCENARIO 5: User Cancels")
    print("="*70)
    print("User changes their mind and cancels\n")
    
    user_id = setup_test_user()
    
    conversation = [
        "I studied for a while",
        "Actually, never mind, forget it"
    ]
    
    simulate_conversation(user_id, conversation)


def interactive_mode():
    """Run in interactive mode where you can type messages."""
    print("\n" + "="*70)
    print("INTERACTIVE MODE")
    print("="*70)
    print("Chat with the progress tracking assistant!")
    print("Type 'quit' to exit\n")
    
    user_id = setup_test_user()
    state = None
    
    while True:
        user_message = input("You: ").strip()
        
        if user_message.lower() in ['quit', 'exit', 'q']:
            print("Goodbye! 👋")
            break
        
        if not user_message:
            continue
        
        result = run_progress_tracking(
            user_id=user_id,
            user_message=user_message,
            conversation_state=state
        )
        
        print(f"Assistant: {result['response']}\n")
        
        # Update state
        state = result["state"]
        
        # Check if done
        if result["done"]:
            if result["success"]:
                print("✅ Progress logged! Starting fresh conversation.\n")
            else:
                print("Conversation ended. Starting fresh.\n")
            state = None  # Reset for new conversation


def main():
    """Run all demo scenarios."""
    print("\n" + "="*70)
    print("PROGRESS TRACKING WORKFLOW - CONVERSATIONAL DEMO")
    print("="*70)
    print("This demo shows how the workflow handles natural language input")
    print("and asks follow-up questions when information is missing.\n")
    
    # Initialize database
    init_db()
    
    # Run demo scenarios
    demo_scenario_1()
    input("\nPress Enter to continue to next scenario...")
    
    demo_scenario_2()
    input("\nPress Enter to continue to next scenario...")
    
    demo_scenario_3()
    input("\nPress Enter to continue to next scenario...")
    
    demo_scenario_4()
    input("\nPress Enter to continue to next scenario...")
    
    demo_scenario_5()
    input("\nPress Enter to try interactive mode...")
    
    # Interactive mode
    interactive_mode()


if __name__ == "__main__":
    main()
