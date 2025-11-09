"""Node functions for progress tracking workflow."""
import json
from sqlalchemy import select
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from database import get_db_session
from database.models import Assignment, UserAssignment
from shared.config import Configuration
from shared.utils import get_text_llm
from agents.task_agents.progress_tracking.state import ProgressLoggingState
from agents.task_agents.progress_tracking.prompts import (
    PARSE_USER_INPUT_PROMPT,
    IDENTIFY_ASSIGNMENT_PROMPT,
    ASK_FOR_MISSING_INFO_PROMPT,
    CONFIRM_AND_LOG_PROMPT,
    GENERATE_SUCCESS_MESSAGE_PROMPT,
)
from agents.task_agents.progress_tracking.tools import log_study_progress, get_assignment_progress


def parse_user_input_node(state: ProgressLoggingState) -> dict:
    """Parse user's natural language input to extract structured data.
    
    Uses LLM to understand what the user said and extract:
    - Assignment reference
    - Duration
    - Focus/quality ratings
    - Intent (is this a progress update?)
    """
    messages = state["messages"]
    user_input = messages[-1].content if messages else ""
    
    # Build context from previous messages
    context = ""
    if len(messages) > 1:
        context = "\n".join([
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in messages[:-1]
        ])
    
    # Call LLM to parse
    cfg = Configuration()
    llm = get_text_llm(cfg)
    prompt = PARSE_USER_INPUT_PROMPT.format(
        context=context or "First message",
        user_input=user_input
    )
    
    response = llm.invoke([SystemMessage(content=prompt)])
    
    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        # Fallback if LLM doesn't return valid JSON
        parsed = {"intent": "other", "confidence": "low"}
    
    # Update state with parsed info
    updates = {
        "notes": parsed.get("notes", state.get("notes", ""))
    }
    
    # Only update if we got new info (don't overwrite with null)
    if parsed.get("assignment_reference"):
        updates["assignment_candidates"] = [{"reference": parsed["assignment_reference"]}]
    
    if parsed.get("duration", {}).get("minutes"):
        updates["minutes"] = parsed["duration"]["minutes"]
        if not parsed["duration"].get("is_estimate"):
            updates["needs_confirmation"] = False
        else:
            updates["needs_confirmation"] = True
            updates["notes"] = updates["notes"] + f" (User said: {parsed['duration'].get('original_text', '')})"
    
    if parsed.get("focus_level"):
        updates["focus_rating"] = parsed["focus_level"]
    
    if parsed.get("quality_level"):
        updates["quality_rating"] = parsed["quality_level"]
    
    # Check for cancellation
    if parsed.get("intent") == "cancel" or any(word in user_input.lower() for word in ["cancel", "never mind", "forget it"]):
        updates["cancelled"] = True
    
    # Check for confirmation
    if state.get("needs_confirmation") and any(word in user_input.lower() for word in ["yes", "yeah", "correct", "right", "yep"]):
        updates["confirmed"] = True
    
    return updates


def identify_assignment_node(state: ProgressLoggingState) -> dict:
    """Match user's assignment reference to actual assignments in database.
    
    Uses fuzzy matching and LLM to find the best match.
    """
    if state.get("assignment_id"):
        return {}  # Already identified
    
    candidates = state.get("assignment_candidates")
    if not candidates or not candidates[0].get("reference"):
        return {}  # No reference to match
    
    reference = candidates[0]["reference"]
    user_id = state["user_id"]
    
    # Get user's assignments
    with get_db_session() as session:
        stmt = (
            select(Assignment, UserAssignment)
            .join(UserAssignment, Assignment.id == UserAssignment.assignment_id)
            .where(UserAssignment.user_id == user_id)
        )
        results = session.execute(stmt).all()
        
        assignments_list = [
            {
                "id": assignment.id,
                "name": assignment.title,
                "course": assignment.course.title if assignment.course else "Unknown",
                "deadline": assignment.due_at.strftime("%Y-%m-%d") if assignment.due_at else None
            }
            for assignment, _ in results
        ]
    
    if not assignments_list:
        return {"assignment_candidates": None}
    
    # Use LLM to match
    cfg = Configuration()
    llm = get_text_llm(cfg)
    
    assignments_str = "\n".join([
        f"{i+1}. {a['name']} (Course: {a['course']}, ID: {a['id']})"
        for i, a in enumerate(assignments_list)
    ])
    
    prompt = IDENTIFY_ASSIGNMENT_PROMPT.format(
        assignment_reference=reference,
        assignments_list=assignments_str
    )
    
    response = llm.invoke([SystemMessage(content=prompt)])
    
    try:
        result = json.loads(response.content)
        matches = result.get("matches", [])
        
        if not matches:
            return {"assignment_candidates": None}
        
        # If high confidence match (>0.8), auto-select it
        top_match = matches[0]
        if top_match["confidence"] > 0.8 and len(matches) == 1:
            return {
                "assignment_id": top_match["assignment_id"],
                "assignment_candidates": matches
            }
        
        # Otherwise, keep candidates for user to choose
        return {"assignment_candidates": matches}
        
    except (json.JSONDecodeError, KeyError):
        # Fallback: simple string matching
        reference_lower = reference.lower()
        simple_matches = []
        
        for a in assignments_list:
            name_lower = a["name"].lower()
            if reference_lower in name_lower or name_lower in reference_lower:
                simple_matches.append({
                    "assignment_id": a["id"],
                    "assignment_name": a["name"],
                    "confidence": 0.7,
                    "reason": "Name contains reference"
                })
        
        if len(simple_matches) == 1:
            return {
                "assignment_id": simple_matches[0]["assignment_id"],
                "assignment_candidates": simple_matches
            }
        
        return {"assignment_candidates": simple_matches if simple_matches else None}


def check_completeness_node(state: ProgressLoggingState) -> dict:
    """Check what information is still missing."""
    missing = []
    
    if not state.get("assignment_id"):
        missing.append("assignment")
    
    if not state.get("minutes"):
        missing.append("duration")
    
    if state.get("focus_rating") is None:
        missing.append("focus")
    
    if state.get("quality_rating") is None:
        missing.append("quality")
    
    return {"missing_fields": missing}


def ask_for_info_node(state: ProgressLoggingState) -> dict:
    """Generate a natural follow-up question for missing information."""
    missing = state.get("missing_fields", [])
    
    if not missing:
        return {}
    
    # Determine what we have
    have_fields = []
    if state.get("assignment_id"):
        have_fields.append("assignment")
    if state.get("minutes"):
        have_fields.append("duration")
    if state.get("focus_rating") is not None:
        have_fields.append("focus")
    if state.get("quality_rating") is not None:
        have_fields.append("quality")
    
    # Build context
    context_parts = []
    if state.get("notes"):
        context_parts.append(f"User mentioned: {state['notes']}")
    if state.get("assignment_candidates"):
        candidates = state["assignment_candidates"]
        if candidates and len(candidates) > 1:
            context_parts.append(f"Multiple assignment matches found: {[c.get('assignment_name', 'Unknown') for c in candidates]}")
    
    context = " ".join(context_parts) if context_parts else "Starting fresh"
    
    # Use LLM to generate question
    cfg = Configuration()
    llm = get_text_llm(cfg)
    
    prompt = ASK_FOR_MISSING_INFO_PROMPT.format(
        have_fields=", ".join(have_fields) if have_fields else "nothing yet",
        missing_fields=", ".join(missing),
        context=context
    )
    
    response = llm.invoke([SystemMessage(content=prompt)])
    question = response.content
    
    return {
        "messages": [AIMessage(content=question)]
    }


def confirm_data_node(state: ProgressLoggingState) -> dict:
    """Generate confirmation message before logging."""
    # Get assignment name
    assignment_id = state["assignment_id"]
    with get_db_session() as session:
        stmt = select(Assignment).where(Assignment.id == assignment_id)
        assignment = session.execute(stmt).scalar_one()
        assignment_name = assignment.title
    
    minutes = state["minutes"]
    hours = round(minutes / 60, 1)
    focus_rating = state.get("focus_rating", 3)
    quality_rating = state.get("quality_rating", 3)
    notes = state.get("notes", "")
    
    notes_section = f"- Notes: {notes}" if notes else ""
    
    cfg = Configuration()
    llm = get_text_llm(cfg)
    
    prompt = CONFIRM_AND_LOG_PROMPT.format(
        assignment_name=assignment_name,
        minutes=minutes,
        hours=hours,
        focus_rating=focus_rating,
        quality_rating=quality_rating,
        notes_section=notes_section
    )
    
    response = llm.invoke([SystemMessage(content=prompt)])
    confirmation_message = response.content
    
    return {
        "messages": [AIMessage(content=confirmation_message)],
        "needs_confirmation": True
    }


def log_progress_node(state: ProgressLoggingState) -> dict:
    """Actually log the study progress to database."""
    result = log_study_progress(
        user_id=state["user_id"],
        assignment_id=state["assignment_id"],
        minutes=state["minutes"],
        focus_rating=state.get("focus_rating", 3),
        quality_rating=state.get("quality_rating", 3),
        notes=state.get("notes", ""),
        study_block_id=state.get("study_block_id")
    )
    
    if not result["success"]:
        return {
            "success": False,
            "result_message": f"Sorry, there was an error logging your progress: {result.get('error', 'Unknown error')}"
        }
    
    # Generate success message
    progress = result["assignment_progress"]
    
    # Get assignment name
    with get_db_session() as session:
        stmt = select(Assignment).where(Assignment.id == state["assignment_id"])
        assignment = session.execute(stmt).scalar_one()
        assignment_name = assignment.title
    
    # Get recent averages
    recent_progress = get_assignment_progress(state["user_id"], state["assignment_id"])
    
    cfg = Configuration()
    llm = get_text_llm(cfg)
    
    prompt = GENERATE_SUCCESS_MESSAGE_PROMPT.format(
        assignment_name=assignment_name,
        minutes=state["minutes"],
        hours=round(state["minutes"] / 60, 1),
        total_hours_done=progress["hours_done"],
        hours_remaining=progress["hours_remaining"],
        status=progress["status"],
        focus_rating=state.get("focus_rating", 3),
        quality_rating=state.get("quality_rating", 3),
        recent_focus_avg=recent_progress.get("recent_focus_avg", 3),
        recent_quality_avg=recent_progress.get("recent_quality_avg", 3)
    )
    
    response = llm.invoke([SystemMessage(content=prompt)])
    success_message = response.content
    
    return {
        "success": True,
        "result_message": success_message,
        "logged_data": {
            "assignment_id": state["assignment_id"],
            "minutes": state["minutes"],
            "focus_rating": state.get("focus_rating", 3),
            "quality_rating": state.get("quality_rating", 3),
            "progress": progress
        },
        "messages": [AIMessage(content=success_message)]
    }


def handle_cancellation_node(state: ProgressLoggingState) -> dict:
    """Handle when user cancels the logging."""
    return {
        "success": False,
        "result_message": "No problem! Progress logging cancelled. Let me know if you want to log something later! 👍",
        "messages": [AIMessage(content="No problem! Cancelled. Let me know if you need anything else! 👍")]
    }
