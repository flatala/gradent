"""Tools that invoke workflow subgraphs."""
import json
import logging
import os
import time
from typing import Annotated, List, Optional
from time import perf_counter

from langchain_core.tools import tool, InjectedToolArg
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage

from workflows.scheduler import scheduler_graph, SchedulerState
from shared.config import Configuration
from shared.utils import get_text_llm

_logger = logging.getLogger("chat")


@tool
async def run_scheduler_workflow(
    meeting_name: str,
    duration_minutes: int,
    topic: Optional[str] = None,
    event_description: Optional[str] = None,
    attendee_emails: Optional[List[str]] = None,
    location: Optional[str] = None,
    constraints: Optional[str] = None,
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Schedule an event intelligently by checking calendars and finding optimal times.

    Use this tool when the user asks you to:
    - Schedule a meeting or event
    - Find a time that works for multiple people
    - Book calendar time (solo or group)
    - Arrange a meeting with specific constraints

    The scheduler workflow autonomously:
    - Checks calendar availability for all attendees
    - Analyzes scheduling constraints (time preferences, etc.)
    - Finds the optimal time slot
    - Creates a detailed calendar event with invitations

    Args:
        meeting_name: Title of the event (e.g., 'Team Standup', 'Q1 Planning')
        duration_minutes: Event duration in minutes
        topic: Meeting topic/agenda (optional, used in description)
        event_description: Additional details for the event (optional)
        attendee_emails: Optional list of attendee emails to coordinate with
        location: Meeting location - physical address or 'Google Meet' (optional)
        constraints: Optional scheduling preferences (e.g., 'mornings only', 'after 2pm')
        config: Injected configuration (automatically provided)

    Returns:
        Event details with meeting link and confirmation (as JSON string)
    """
    cfg = Configuration.from_runnable_config(config)
    if _logger:
        try:
            _logger.info(
                "TOOL CALL: run_scheduler_workflow | meeting=%s | duration=%d | attendees=%d",
                meeting_name,
                duration_minutes,
                len(attendee_emails) if attendee_emails else 0,
            )
        except Exception:
            pass

    start = perf_counter()

    # Build comprehensive event description
    description_parts = []
    if topic:
        description_parts.append(f"Topic: {topic}")
    if event_description:
        description_parts.append(event_description)
    full_description = "\n\n".join(description_parts) if description_parts else meeting_name

    # Create initial state
    initial_state = SchedulerState(
        meeting_name=meeting_name,
        topic=topic,
        event_description=full_description,
        duration_minutes=duration_minutes,
        attendee_emails=attendee_emails or [],
        location=location,
        constraints=constraints,
    )

    # Retry loop for transient errors
    max_attempts = int(os.getenv("SCHEDULER_RETRIES", "2"))
    backoff = float(os.getenv("SCHEDULER_BACKOFF", "2.0"))
    last_exc: Exception | None = None
    result = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = await scheduler_graph.ainvoke(initial_state, config)
            break
        except Exception as e:
            last_exc = e
            if _logger:
                try:
                    _logger.info("TOOL RETRY %d/%d due to error: %r", attempt, max_attempts, e)
                except Exception:
                    pass
            if attempt < max_attempts:
                time.sleep(backoff)
            else:
                result = None

    # Check if scheduling succeeded
    if result and result.get("scheduled_event"):
        event = result["scheduled_event"]
        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: run_scheduler_workflow | status=success | duration=%.2fs | event_id=%s",
                    perf_counter() - start,
                    event.event_id if hasattr(event, 'event_id') else 'unknown',
                )
            except Exception:
                pass

        return json.dumps({
            "status": "success",
            "meeting_name": event.title if hasattr(event, 'title') else meeting_name,
            "event_id": event.event_id if hasattr(event, 'event_id') else None,
            "calendar_link": event.calendar_link if hasattr(event, 'calendar_link') else None,
            "meeting_link": event.meeting_link if hasattr(event, 'meeting_link') else None,
            "scheduled_time": event.start_time if hasattr(event, 'start_time') else None,
            "duration_minutes": event.duration_minutes if hasattr(event, 'duration_minutes') else duration_minutes,
            "attendees": event.attendees if hasattr(event, 'attendees') else attendee_emails or [],
            "location": event.location if hasattr(event, 'location') else location,
            "description": event.description if hasattr(event, 'description') else full_description,
            "reasoning": result.get("reasoning", "Event scheduled successfully"),
        }, indent=2)

    # Scheduling failed
    if _logger:
        try:
            _logger.info(
                "TOOL DONE: run_scheduler_workflow | status=failed | duration=%.2fs",
                perf_counter() - start,
            )
        except Exception:
            pass

    failure_reason = result.get("reasoning") if result else None
    if last_exc:
        failure_reason = f"Backend error: {last_exc}"
    elif not failure_reason:
        failure_reason = "Could not find suitable time or create event"

    return json.dumps({
        "status": "failed",
        "reason": failure_reason,
    }, indent=2)
