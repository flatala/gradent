"""State definition for the scheduler workflow."""
from typing import List, Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field
from langgraph.graph import add_messages


class ScheduledEvent(BaseModel):
    """A scheduled calendar event with all details."""
    event_id: str = Field(description="Google Calendar event ID")
    title: str = Field(description="Event title/name")
    description: Optional[str] = Field(default=None, description="Event description")
    start_time: str = Field(description="Event start time (ISO 8601 format)")
    end_time: str = Field(description="Event end time (ISO 8601 format)")
    duration_minutes: int = Field(description="Event duration in minutes")
    attendees: List[str] = Field(default_factory=list, description="List of attendee email addresses")
    location: Optional[str] = Field(default=None, description="Meeting location or 'Google Meet'")
    meeting_link: Optional[str] = Field(default=None, description="Google Meet link or conferencing URL")
    calendar_link: Optional[str] = Field(default=None, description="Link to view event in Google Calendar")


class SchedulerState(BaseModel):
    """State for the scheduler workflow.

    This state tracks the scheduling process including:
    - Meeting details (name, topic, description, duration)
    - Attendees and location information
    - Scheduling constraints and preferences
    - Message history for agent interactions
    - Available time slots discovered
    - The final scheduled event
    """

    # Input: Meeting details
    meeting_name: str = Field(description="Title/subject of the event (e.g., 'Team Standup', 'Q1 Planning')")
    topic: Optional[str] = Field(
        default=None,
        description="Meeting topic/agenda (used in description)"
    )
    event_description: str = Field(
        default="",
        description="Detailed event description combining topic and additional context"
    )
    duration_minutes: int = Field(description="Event duration in minutes")

    # Input: Attendees and location
    attendee_emails: List[str] = Field(
        default_factory=list,
        description="List of attendee email addresses to coordinate with"
    )
    location: Optional[str] = Field(
        default=None,
        description="Physical location or 'Google Meet' for virtual meetings"
    )

    # Input: Scheduling time preferences (structured)
    preferred_start: Optional[str] = Field(
        default=None,
        description="Preferred start time in ISO 8601 format (e.g., '2025-01-15T14:00:00')"
    )
    preferred_end: Optional[str] = Field(
        default=None,
        description="Preferred end time in ISO 8601 format (e.g., '2025-01-15T15:00:00')"
    )
    date_range_start: Optional[str] = Field(
        default=None,
        description="Start of date range to search for availability (ISO 8601 date, e.g., '2025-01-15')"
    )
    date_range_end: Optional[str] = Field(
        default=None,
        description="End of date range to search for availability (ISO 8601 date, e.g., '2025-01-20')"
    )
    time_constraints: Optional[str] = Field(
        default=None,
        description="Additional time constraints (e.g., 'mornings only', 'avoid Mondays', 'working hours only')"
    )

    # Message history (append-only merge using LangGraph's add_messages reducer)
    messages: Annotated[list, add_messages] = Field(
        default_factory=list,
        description="LLM conversation history for scheduling agent"
    )

    # Authentication status
    auth_required: bool = Field(
        default=False,
        description="Whether Google Calendar authentication is required"
    )
    auth_message: Optional[str] = Field(
        default=None,
        description="Authentication message/instructions if auth is needed"
    )

    # Output
    scheduled_event: Optional[ScheduledEvent] = Field(
        default=None,
        description="The final scheduled event with all details"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Agent's scheduling rationale or failure reason"
    )

    class Config:
        arbitrary_types_allowed = True
