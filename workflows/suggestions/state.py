"\"\"\"State definition for the suggestions workflow.\"\"\""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Dict, List, Optional

from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class Suggestion(BaseModel):
    """Structured suggestion returned by the workflow."""

    title: str
    message: str
    category: str
    suggested_time: Optional[str] = None
    priority: Optional[str] = None
    linked_assignments: List[int] = Field(default_factory=list)
    linked_events: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


class SuggestionsState(BaseModel):
    """State for generating proactive study suggestions."""

    user_id: int
    snapshot_ts: datetime = Field(default_factory=datetime.utcnow)

    # Context assembled from DB / vector store
    assignments: Dict[str, List[dict]] = Field(default_factory=dict)
    calendar_events: List[dict] = Field(default_factory=list)
    study_history: List[dict] = Field(default_factory=list)
    new_resources: List[dict] = Field(default_factory=list)

    # LLM scratchpad and output
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    suggestions: Optional[List[Suggestion]] = None

    class Config:
        arbitrary_types_allowed = True

