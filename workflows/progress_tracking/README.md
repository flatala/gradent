# Progress Tracking Workflow

A conversational LangGraph workflow that enables students to log study progress through natural language interaction.

## Overview

Instead of requiring structured data upfront, this workflow:
1. **Parses natural language** input using LLM
2. **Asks follow-up questions** when information is missing
3. **Fuzzy matches assignments** when references are vague
4. **Confirms before logging** to ensure accuracy
5. **Provides encouraging feedback** after successful logging

## Architecture

### Components

- **`state.py`**: Defines `ProgressLoggingState` that tracks conversation and extracted data
- **`nodes.py`**: Individual node functions for each workflow step
- **`prompts.py`**: LLM prompts for parsing, matching, and generating responses
- **`graph.py`**: LangGraph workflow that connects nodes with conditional edges
- **`tools.py`**: Database functions (`log_study_progress`, `get_assignment_progress`, etc.)

### Workflow Flow

```
User Input
    ↓
parse_user_input (LLM extracts structured data)
    ↓
identify_assignment (fuzzy match to DB assignments)
    ↓
check_completeness (what's missing?)
    ↓
    ├─→ [Complete] → confirm_data → [wait for confirmation] → log_progress → END
    ├─→ [Missing critical info] → ask_for_info → END (wait for user response)
    ├─→ [Only optional missing] → use_defaults → confirm_data → ...
    └─→ [Cancelled] → handle_cancellation → END
```

### Conversation Loop

The workflow is **stateful** - it maintains conversation history and extracted data across multiple turns:

1. User sends initial message: "I studied the RL assignment"
2. System asks: "About how long did you study?"
3. User responds: "90 minutes"
4. System asks: "How focused were you (1-5)?"
5. User responds: "Pretty focused, like a 4"
6. System confirms: "Let me confirm - 90 minutes on RL Project, focus 4/5..."
7. User responds: "yes"
8. System logs and responds: "✅ Logged 1.5 hours..."

## Usage

### Basic Usage

```python
from workflows.progress_tracking import run_progress_tracking

# Start conversation
result = run_progress_tracking(
    user_id=1,
    user_message="I worked on assignment 1 for 90 minutes"
)

print(result["response"])  # Assistant's reply
print(result["done"])      # True if logging complete
print(result["success"])   # True if successfully logged

# Continue conversation
if not result["done"]:
    result2 = run_progress_tracking(
        user_id=1,
        user_message="It was pretty focused",
        conversation_state=result["state"]  # Pass previous state
    )
```

### Multi-Turn Conversation

```python
state = None
user_messages = [
    "I just finished studying",
    "The neural networks assignment",
    "About 2 hours",
    "yes"  # Confirm
]

for msg in user_messages:
    result = run_progress_tracking(
        user_id=1,
        user_message=msg,
        conversation_state=state
    )
    print(f"User: {msg}")
    print(f"Assistant: {result['response']}\n")
    
    state = result["state"]
    
    if result["done"]:
        break
```

## What Gets Extracted

### Required Fields
- **Assignment**: Which assignment they worked on
  - Fuzzy matching: "RL project" → "Reinforcement Learning Project"
  - Handles: assignment numbers, partial names, keywords
- **Duration**: How long they studied
  - Explicit: "90 minutes", "1.5 hours", "2h 30m"
  - Vague: "a while" (system will ask for specifics)

### Optional Fields
- **Focus Rating** (1-5): How focused they were
  - Keywords: "very focused" → 4-5, "distracted" → 1-2
  - Default: 3 if not specified after asking
- **Quality Rating** (1-5): How productive they were
  - Keywords: "finished", "made progress" → 4-5, "stuck" → 1-2
  - Default: 3 if not specified after asking

### Additional Context
- **Notes**: Any free-text context
- **Study Block ID**: If linked to a scheduled study block

## Example Conversations

### Scenario 1: Complete Info Upfront
```
User: I worked on the RL project for 90 minutes and was really focused, made good progress!
Assistant: Great! Let me confirm - you studied **Reinforcement Learning Project** for **90 minutes** (1.5 hours), 
           with focus level **5/5** and quality **5/5**. Does this look right?
User: yes
Assistant: ✅ Logged 1.5 hours on **Reinforcement Learning Project**! You've completed 1.5 hours total, 
           8.5 hours remaining. Excellent focus (5/5) - keep up the great work! 🎯
```

### Scenario 2: Vague Reference
```
User: I studied assignment 2
Assistant: I found a few assignments. Did you work on: 1) Assignment 2: ML Basics, or 2) Neural Networks Lab?
User: The ML one
Assistant: Got it! About how long did you study for?
User: An hour
Assistant: How focused were you? (1=very distracted, 5=deep focus)
User: Pretty good, 4
Assistant: Great! Let me confirm - you studied **Assignment 2: ML Basics** for **60 minutes** (1 hour), 
           with focus level **4/5** and quality **3/5** (default). Does this look right?
User: yes
Assistant: ✅ Logged 1 hour on **Assignment 2: ML Basics**! ...
```

### Scenario 3: Very Vague
```
User: I just finished studying
Assistant: Which assignment did you work on?
User: The RL one
Assistant: About how long did you study for?
User: Maybe 45 minutes
Assistant: How focused were you during this session? (1=very distracted, 5=deep focus)
User: I'd say 3
Assistant: Great! Let me confirm - you studied **Reinforcement Learning Project** for **45 minutes** (0.8 hours), 
           with focus level **3/5** and quality **3/5** (default). Does this look right?
User: yes
Assistant: ✅ Logged 0.8 hours on **Reinforcement Learning Project**! ...
```

## Testing

### Run Demo Scenarios
```bash
poetry run python tests/test_progress_tracking_conversation.py
```

This will run 5 demo scenarios showing different conversation patterns, then enter interactive mode where you can chat with the assistant.

### Run Unit Tests
```bash
poetry run python tests/test_progress_tracking.py
```

Tests the underlying `log_study_progress()` and related database functions.

## Integration

### With Main Agent

The main agent can invoke this workflow when it detects progress logging intent:

```python
from workflows.progress_tracking import run_progress_tracking

# In main agent's tool routing
if intent == "log_progress":
    result = run_progress_tracking(
        user_id=state["user_id"],
        user_message=state["user_message"],
        conversation_state=state.get("progress_tracking_state")
    )
    
    if not result["done"]:
        # Store state for next turn
        state["progress_tracking_state"] = result["state"]
        return result["response"]
    else:
        # Logging complete
        state["progress_tracking_state"] = None
        return result["response"]
```

### As Standalone Tool

Can also be exposed as a standalone conversational tool that the main agent calls:

```python
@tool
def track_study_progress(user_input: str) -> str:
    """Log study progress through natural conversation.
    
    Args:
        user_input: User's natural language message about their study session
        
    Returns:
        Assistant's response (question or confirmation)
    """
    result = run_progress_tracking(
        user_id=current_user_id,
        user_message=user_input,
        conversation_state=get_conversation_state()
    )
    
    save_conversation_state(result["state"])
    return result["response"]
```

## Future Enhancements

1. **Study Block Integration**: Automatically detect if user is completing a scheduled study block
2. **Pattern Recognition**: "I see you often study RL on Tuesdays - want to schedule this weekly?"
3. **Proactive Check-ins**: "Haven't heard from you today - did you study?"
4. **Voice Input**: Optimize prompts for transcribed voice input
5. **Multi-Assignment Sessions**: "I studied RL for 60 min and ML for 30 min"
6. **Time Tracking Integration**: Auto-detect study sessions from calendar/time tracking tools
