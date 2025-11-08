"""State definition for progress tracking workflow."""
from typing import TypedDict, Optional, Annotated
from operator import add


class ProgressLoggingState(TypedDict):
    """State for the conversational progress tracking workflow.
    
    This workflow helps users log study progress through natural conversation,
    asking follow-up questions when needed.
    """
    # User context
    user_id: int
    
    # Conversation
    messages: Annotated[list, add]  # Accumulated conversation history
    
    # Extracted/confirmed data for log_study_progress
    assignment_id: Optional[int]
    assignment_candidates: Optional[list]  # [{"id": 1, "name": "...", "score": 0.8}]
    minutes: Optional[int]
    focus_rating: Optional[int]  # 1-5
    quality_rating: Optional[int]  # 1-5
    notes: str
    study_block_id: Optional[int]  # If user mentions a scheduled block
    
    # Workflow control
    missing_fields: list  # ["assignment", "duration", "focus", "quality"]
    needs_confirmation: bool  # True if we made assumptions
    confirmed: bool  # User confirmed the data
    cancelled: bool  # User cancelled the logging
    
    # Result
    success: bool
    result_message: str  # Final message to show user
    logged_data: Optional[dict]  # The actual data that was logged
