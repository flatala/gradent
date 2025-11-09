"""LangGraph workflow for conversational progress tracking.

This workflow enables natural language interaction for logging study progress.
It asks follow-up questions when information is missing and confirms before logging.
"""
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from workflows.progress_tracking.state import ProgressLoggingState
from workflows.progress_tracking.nodes import (
    parse_user_input_node,
    identify_assignment_node,
    check_completeness_node,
    ask_for_info_node,
    confirm_data_node,
    log_progress_node,
    handle_cancellation_node,
)


def should_continue(state: ProgressLoggingState) -> str:
    """Determine next step based on current state."""
    # Check for cancellation
    if state.get("cancelled"):
        return "cancel"
    
    # If we need confirmation and user hasn't confirmed yet
    if state.get("needs_confirmation") and not state.get("confirmed"):
        return "wait_for_confirmation"
    
    # Check if we have all required fields
    missing = state.get("missing_fields", [])
    
    # Focus and quality are optional (we can default to 3)
    critical_missing = [f for f in missing if f in ["assignment", "duration"]]
    
    if critical_missing:
        return "ask"
    
    # If we only need focus/quality and have asked twice, use defaults
    if missing and len(state.get("messages", [])) > 6:
        # Been asking too long, just use defaults
        return "use_defaults"
    
    # If we have assignment candidates but no confirmed assignment_id
    if state.get("assignment_candidates") and not state.get("assignment_id"):
        candidates = state["assignment_candidates"]
        if len(candidates) > 1:
            return "ask"  # Need clarification
    
    # If everything is ready and confirmed (or doesn't need confirmation)
    if state.get("confirmed") or not state.get("needs_confirmation"):
        # Check one more time if we have everything critical
        if not state.get("assignment_id") or not state.get("minutes"):
            return "ask"
        return "log"
    
    # Need to confirm
    return "confirm"


def use_defaults_node(state: ProgressLoggingState) -> dict:
    """Use default values for optional fields that are still missing."""
    updates = {}
    
    if state.get("focus_rating") is None:
        updates["focus_rating"] = 3
    
    if state.get("quality_rating") is None:
        updates["quality_rating"] = 3
    
    updates["missing_fields"] = []
    updates["confirmed"] = True  # Auto-confirm defaults
    
    return updates


def create_progress_tracking_graph():
    """Create the LangGraph workflow for progress tracking."""
    workflow = StateGraph(ProgressLoggingState)
    
    # Add nodes
    workflow.add_node("parse_input", parse_user_input_node)
    workflow.add_node("identify_assignment", identify_assignment_node)
    workflow.add_node("check_completeness", check_completeness_node)
    workflow.add_node("ask_for_info", ask_for_info_node)
    workflow.add_node("use_defaults", use_defaults_node)
    workflow.add_node("confirm_data", confirm_data_node)
    workflow.add_node("log_progress", log_progress_node)
    workflow.add_node("handle_cancellation", handle_cancellation_node)
    
    # Set entry point
    workflow.set_entry_point("parse_input")
    
    # Define flow
    workflow.add_edge("parse_input", "identify_assignment")
    workflow.add_edge("identify_assignment", "check_completeness")
    
    # From check_completeness, decide what to do
    workflow.add_conditional_edges(
        "check_completeness",
        should_continue,
        {
            "ask": "ask_for_info",
            "confirm": "confirm_data",
            "log": "log_progress",
            "cancel": "handle_cancellation",
            "use_defaults": "use_defaults",
            "wait_for_confirmation": END  # Wait for user response
        }
    )
    
    # After asking, we END and wait for user to respond
    workflow.add_edge("ask_for_info", END)
    
    # After using defaults, go straight to confirmation
    workflow.add_edge("use_defaults", "confirm_data")
    
    # After confirmation message, END and wait for user confirmation
    workflow.add_edge("confirm_data", END)
    
    # After logging, we're done
    workflow.add_edge("log_progress", END)
    workflow.add_edge("handle_cancellation", END)
    
    return workflow.compile()


# Create the compiled graph
progress_tracking_graph = create_progress_tracking_graph()


def run_progress_tracking(user_id: int, user_message: str, conversation_state: dict = None):
    """Run the progress tracking workflow with a user message.
    
    Args:
        user_id: The user's ID
        user_message: The user's natural language input
        conversation_state: Optional previous state to continue conversation
        
    Returns:
        dict with:
        - response: The assistant's response message
        - state: The updated conversation state
        - done: Whether logging is complete
        - success: Whether logging was successful (if done)
    """
    # Initialize or continue state
    if conversation_state is None:
        state = {
            "user_id": user_id,
            "messages": [HumanMessage(content=user_message)],
            "assignment_id": None,
            "assignment_candidates": None,
            "minutes": None,
            "focus_rating": None,
            "quality_rating": None,
            "notes": "",
            "study_block_id": None,
            "missing_fields": [],
            "needs_confirmation": False,
            "confirmed": False,
            "cancelled": False,
            "success": False,
            "result_message": "",
            "logged_data": None,
        }
    else:
        state = conversation_state.copy()
        state["messages"] = state.get("messages", []) + [HumanMessage(content=user_message)]
    
    # Run the graph
    result = progress_tracking_graph.invoke(state)
    
    # Extract response
    messages = result.get("messages", [])
    last_message = messages[-1] if messages else None
    response = last_message.content if last_message else "I'm not sure what to say..."
    
    # Check if done
    done = result.get("success") is not None  # Success is set when logging completes or cancels
    success = result.get("success", False)
    
    return {
        "response": response,
        "state": result,
        "done": done,
        "success": success,
        "logged_data": result.get("logged_data")
    }
