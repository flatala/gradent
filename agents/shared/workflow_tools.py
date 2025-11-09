"""Tools that invoke workflow subgraphs."""
from __future__ import annotations
import json
import logging
import os
import time
from datetime import datetime
from time import perf_counter
from typing import Annotated, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from database.connection import get_db_session
from database.models import (
    Suggestion,
    SuggestionStatus,
    User,
    Assignment,
    UserAssignment,
    AssignmentStatus,
    AssignmentAssessment,
)
from agents.task_agents.scheduler import scheduler_graph, SchedulerState
from agents.task_agents.assignment_assessment import assessment_graph, AssessmentState, AssignmentInfo
from shared.config import Configuration
from shared.utils import get_text_llm
from agents.task_agents.suggestions import SuggestionsState, Suggestion as WorkflowSuggestion, suggestions_graph
from agents.task_agents.progress_tracking.graph import progress_tracking_graph
from agents.task_agents.progress_tracking.state import ProgressLoggingState
from context_updater.ingestion import ContextUpdater

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
    user_id: Optional[int] = None,
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
        user_id: User ID for the scheduler (defaults to 1)
        config: Injected configuration (automatically provided)

    Returns:
        Event details with meeting link and confirmation (as JSON string)
    """
    resolved_user_id = _resolve_user_id(user_id)
    
    if _logger:
        try:
            _logger.info(
                "TOOL CALL: run_scheduler_workflow | user_id=%s | meeting=%s | duration=%d | attendees=%d",
                resolved_user_id,
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


@tool
async def assess_assignment(
    title: str,
    description: str,
    course_name: str = "Unknown Course",
    assignment_id: int = None,
    user_id: Optional[int] = None,
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Assess the difficulty and effort required for an assignment.

    Use this tool when the user:
    - Shares an assignment and wants to understand how difficult it is
    - Asks how long an assignment will take
    - Wants help breaking down an assignment into milestones
    - Needs to plan study time for an assignment

    The workflow analyzes the assignment requirements and provides:
    - Effort estimates (low, most likely, high)
    - Difficulty rating
    - Risk score
    - Detailed milestones and timeline
    - Prerequisites and deliverables

    Args:
        title: The assignment title or name
        description: Full assignment description, requirements, or rubric
        course_name: Name of the course (optional)
        assignment_id: Database ID if the assignment already exists (optional)
        user_id: User ID (defaults to 1)
        config: Injected configuration (automatically provided)

    Returns:
        Structured assessment with effort estimates, milestones, and breakdown (as JSON string)
    """
    resolved_user_id = _resolve_user_id(user_id)
    
    if _logger:
        try:
            _logger.info("TOOL CALL: assess_assignment | user_id=%s | title=%s | course=%s", 
                        resolved_user_id, title, course_name)
        except Exception:
            pass

    start = perf_counter()

    # Create initial state
    assignment_info = AssignmentInfo(
        assignment_id=assignment_id,
        title=title,
        description=description,
        course_name=course_name,
    )
    
    initial_state = AssessmentState(
        assignment_info=assignment_info,
        user_id=resolved_user_id
    )
    
    try:
        result = await assessment_graph.ainvoke(initial_state, config)
        
        # Extract assessment
        if result.get("assessment"):
            assessment = result["assessment"]
            if _logger:
                try:
                    _logger.info(
                        "TOOL DONE: assess_assignment | status=ok | duration=%.2fs | effort_most=%.1f hrs | difficulty=%.1f/5",
                        perf_counter() - start,
                        assessment.effort_hours_most,
                        assessment.difficulty_1to5,
                    )
                except Exception:
                    pass
            
            # Return structured JSON
            return json.dumps({
                "title": title,
                "effort_estimates": {
                    "low_hours": assessment.effort_hours_low,
                    "most_likely_hours": assessment.effort_hours_most,
                    "high_hours": assessment.effort_hours_high,
                },
                "difficulty_1to5": assessment.difficulty_1to5,
                "risk_score_0to100": assessment.risk_score_0to100,
                "confidence": assessment.confidence_0to1,
                "milestones": assessment.milestones,
                "prerequisites": assessment.prereq_topics,
                "deliverables": assessment.deliverables,
                "blocking_dependencies": assessment.blocking_dependencies,
                "summary": assessment.summary,
                "saved_to_database": result.get("assessment_record_id") is not None,
            }, indent=2)
        
        # No assessment generated
        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: assess_assignment | status=no_assessment | duration=%.2fs",
                    perf_counter() - start,
                )
            except Exception:
                pass
        return "Assessment workflow completed but no assessment was generated."
    
    except Exception as e:
        if _logger:
            try:
                _logger.error("TOOL ERROR: assess_assignment | error=%s", str(e))
            except Exception:
                pass
        return f"Error assessing assignment: {str(e)}"


def _resolve_user_id(user_id: Optional[int] = None) -> int:
    """Return a valid user id, defaulting to 1.
    
    Args:
        user_id: Optional user ID. If None, defaults to 1.
        
    Returns:
        User ID (defaults to 1 for single-user setup)
    """
    if user_id is not None:
        return user_id
    # Default to user_id=1 for now (single-user setup)
    # In the future, this could check the database or use auth context
    return 1


def _parse_suggested_time(value: Optional[str]) -> Optional[datetime]:
    """Attempt to parse ISO8601 timestamps; otherwise return None."""
    if not value:
        return None
    try:
        # Handle basic ISO formats
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _store_suggestions(
    user_id: int,
    suggestions: list[WorkflowSuggestion],
) -> list[dict]:
    """Persist suggestions in the database and return serializable dicts."""
    serialized: list[dict] = []
    discord_enabled = bool(os.getenv("DISCORD_WEBHOOK_URL"))
    now = datetime.utcnow()

    with get_db_session() as db:
        for item in suggestions:
            suggested_dt = _parse_suggested_time(item.suggested_time)
            existing = (
                db.query(Suggestion)
                .filter(
                    Suggestion.user_id == user_id,
                    Suggestion.title == item.title,
                    Suggestion.message == item.message,
                )
                .order_by(Suggestion.created_at.desc())
                .first()
            )

            channel_config = {
                "discord": discord_enabled,
            }

            if existing:
                existing.category = item.category
                existing.priority = item.priority
                existing.suggested_time = suggested_dt
                existing.suggested_time_text = item.suggested_time
                existing.linked_assignments = item.linked_assignments
                existing.linked_events = item.linked_events
                existing.tags = item.tags
                existing.sources = item.sources
                existing.channel_config = channel_config
                existing.status = SuggestionStatus.PENDING
                existing.updated_at = now
                suggestion_row = existing
            else:
                suggestion_row = Suggestion(
                    user_id=user_id,
                    title=item.title,
                    message=item.message,
                    category=item.category,
                    priority=item.priority,
                    suggested_time=suggested_dt,
                    suggested_time_text=item.suggested_time,
                    linked_assignments=item.linked_assignments,
                    linked_events=item.linked_events,
                    tags=item.tags,
                    sources=item.sources,
                    channel_config=channel_config,
                    status=SuggestionStatus.PENDING,
                    created_at=now,
                )
                db.add(suggestion_row)
                db.flush()

            serialized.append(
                {
                    "id": suggestion_row.id,
                    "user_id": suggestion_row.user_id,
                    "title": suggestion_row.title,
                    "message": suggestion_row.message,
                    "category": suggestion_row.category,
                    "priority": suggestion_row.priority,
                    "suggested_time": suggestion_row.suggested_time.isoformat()
                    if suggestion_row.suggested_time
                    else None,
                    "suggested_time_text": suggestion_row.suggested_time_text,
                    "status": suggestion_row.status.value if suggestion_row.status else None,
                    "channel_config": suggestion_row.channel_config,
                    "linked_assignments": suggestion_row.linked_assignments,
                    "linked_events": suggestion_row.linked_events,
                    "tags": suggestion_row.tags,
                    "sources": suggestion_row.sources,
                }
            )

    return serialized


@tool
async def generate_suggestions(
    user_id: Optional[int] = None,
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Generate proactive study suggestions from assignments, calendar, and study history.

    Use this tool when the user asks for reminders, priorities, next actions,
    or when new Brightspace/calendar updates arrive and you want to surface
    actionable nudges.

    Args:
        user_id: Target user (defaults to 1)
        config: Injected LangChain runnable configuration

    Returns:
        JSON array of suggestions with category, priority, and references.
    """
    resolved_user_id = _resolve_user_id(user_id)

    if _logger:
        try:
            _logger.info("TOOL CALL: generate_suggestions | user_id=%s", resolved_user_id)
        except Exception:
            pass

    state = SuggestionsState(
        user_id=resolved_user_id,
        snapshot_ts=datetime.utcnow(),
    )

    try:
        result = await suggestions_graph.ainvoke(state, config)
    except Exception as exc:  # pragma: no cover - error path
        if _logger:
            try:
                _logger.error("TOOL ERROR: generate_suggestions | error=%s", exc)
            except Exception:
                pass
        return json.dumps({"error": f"Failed to generate suggestions: {exc}"}, indent=2)

    suggestions = result.get("suggestions") or []
    stored_records = _store_suggestions(resolved_user_id, suggestions)
    serialized = stored_records if stored_records else [s.model_dump() if hasattr(s, "model_dump") else s for s in suggestions]

    if _logger:
        try:
            _logger.info(
                "TOOL DONE: generate_suggestions | count=%d",
                len(serialized),
            )
        except Exception:
            pass

    return json.dumps(serialized, indent=2)


@tool
async def log_progress_update(
    user_message: str,
    user_id: Optional[int] = None,
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Log a study progress update through conversational interaction.

    Use this tool when the user wants to:
    - Log time spent studying or working on an assignment
    - Record progress on homework, projects, or exam prep
    - Track study sessions with duration and quality
    - Update how much work they've done on a task

    This workflow provides a conversational interface that:
    - Identifies which assignment they worked on
    - Extracts study duration from natural language (e.g., "2 hours", "90 minutes")
    - Optionally asks for focus and quality ratings (1-5 scale)
    - Confirms the information before logging
    - Handles follow-up questions if information is missing

    Examples of user messages this handles:
    - "I studied calculus for 2 hours"
    - "Worked on the CS assignment for 90 minutes, really focused"
    - "Just finished 1.5 hours on the biology lab report"
    - "Spent 45 mins on math homework but kept getting distracted"

    Args:
        user_message: The user's natural language progress update
        user_id: Target user ID (defaults to 1)
        config: Injected configuration (automatically provided)

    Returns:
        Confirmation message with logged study details (as JSON string)
    """
    resolved_user_id = _resolve_user_id(user_id)

    if _logger:
        try:
            _logger.info(
                "TOOL CALL: log_progress_update | user_id=%s | message=%s",
                resolved_user_id,
                user_message[:100] + "..." if len(user_message) > 100 else user_message
            )
        except Exception:
            pass

    start = perf_counter()

    # Create initial state
    initial_state = ProgressLoggingState(
        user_id=resolved_user_id,
        messages=[HumanMessage(content=user_message)],
        assignment_id=None,
        assignment_candidates=None,
        minutes=None,
        focus_rating=None,
        quality_rating=None,
        notes="",
        study_block_id=None,
        missing_fields=[],
        needs_confirmation=False,
        confirmed=False,
        cancelled=False,
        success=False,
        result_message="",
        logged_data=None,
    )

    try:
        result = await progress_tracking_graph.ainvoke(initial_state, config)
        
        # Extract response
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None
        response = last_message.content if last_message else "I'm not sure how to help with that."
        
        # Check if logging succeeded
        if result.get("success"):
            logged_data = result.get("logged_data")
            if _logger:
                try:
                    _logger.info(
                        "TOOL DONE: log_progress_update | status=success | duration=%.2fs | minutes=%s",
                        perf_counter() - start,
                        logged_data.get("minutes") if logged_data else "unknown"
                    )
                except Exception:
                    pass
            
            # Return structured success response
            return json.dumps({
                "status": "success",
                "message": response,
                "logged_data": logged_data,
                "conversation_complete": True,
            }, indent=2)
        
        # Check if cancelled
        if result.get("cancelled"):
            if _logger:
                try:
                    _logger.info(
                        "TOOL DONE: log_progress_update | status=cancelled | duration=%.2fs",
                        perf_counter() - start,
                    )
                except Exception:
                    pass
            
            return json.dumps({
                "status": "cancelled",
                "message": response,
                "conversation_complete": True,
            }, indent=2)
        
        # Conversation is ongoing (needs more info or confirmation)
        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: log_progress_update | status=ongoing | duration=%.2fs | needs_more_info",
                    perf_counter() - start,
                )
            except Exception:
                pass
        
        return json.dumps({
            "status": "ongoing",
            "message": response,
            "conversation_complete": False,
            "state": {
                "has_assignment": result.get("assignment_id") is not None,
                "has_duration": result.get("minutes") is not None,
                "missing_fields": result.get("missing_fields", []),
                "needs_confirmation": result.get("needs_confirmation", False),
            }
        }, indent=2)
        
    except Exception as e:
        if _logger:
            try:
                _logger.error("TOOL ERROR: log_progress_update | error=%s", str(e))
            except Exception:
                pass
        return json.dumps({
            "status": "error",
            "error": f"Failed to process progress update: {str(e)}"
        }, indent=2)


@tool
async def run_exam_api_workflow(
    pdf_paths: List[str],
    question_header: str,
    question_description: str,
    api_key: str = None,
    api_base_url: str = "http://localhost:3000",
    model_name: str = None,
) -> str:
    """Generate exam questions from PDF files using an external API.

    This tool uploads PDFs to a question generation API and streams back
    generated exam questions in markdown format with MathJax support.

    Use this tool when the user wants to:
    - Create an exam from PDF materials
    - Generate practice questions from course documents
    - Build a test from lecture notes or textbooks

    Args:
        pdf_paths: List of paths to PDF files to process
        question_header: Exam title/header (e.g., "Midterm Exam - CS 101")
        question_description: Requirements for the exam (e.g., "10 MCQ, 5 short answer")
        api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
        api_base_url: API base URL (default: http://localhost:3000)
        model_name: AI model to use (optional)

    Returns:
        Generated exam questions as markdown, or error message

    Example:
        User: "Create a midterm exam from my lecture notes PDF"
        Assistant calls:
        run_exam_api_workflow(
            pdf_paths=["lecture_notes.pdf"],
            question_header="Midterm Exam - Biology 201",
            question_description="15 multiple choice (mixed difficulty), 5 short answer"
        )
    """
    from agents.task_agents.exam_api import exam_api_graph, ExamAPIState
    
    # Use environment variable if api_key not provided
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: No API key provided. Set OPENROUTER_API_KEY environment variable or pass api_key parameter."

    # Create initial state
    state = ExamAPIState(
        pdf_paths=pdf_paths,
        question_header=question_header,
        question_description=question_description,
        api_key=api_key,
        api_base_url=api_base_url,
        model_name=model_name,
    )

    # Run the workflow
    result = await exam_api_graph.ainvoke(state)

    # Return result or error
    if result.error:
        return f"Error generating exam: {result.error}"

    if result.generated_questions:
        return result.generated_questions

    return "No questions were generated. Please check your input parameters and try again."


@tool
async def run_context_update(user_id: int) -> str:
    """Run context update to sync courses and assignments from Brightspace LMS.

    Use this tool when you need to:
    - Sync the latest assignments from Brightspace
    - Update course information
    - Refresh the vector database with new content

    This tool fetches data from the LMS and updates both the SQL database
    and the vector database for RAG.

    Args:
        user_id: Database user ID

    Returns:
        JSON string with sync statistics (courses_synced, assignments_synced, content_indexed)
    """
    if _logger:
        try:
            _logger.info("TOOL CALL: run_context_update | user_id=%d", user_id)
        except Exception:
            pass

    start = perf_counter()

    try:
        context_updater = ContextUpdater(user_id=user_id)
        stats = context_updater.sync_all()

        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: run_context_update | duration=%.2fs | courses=%d | assignments=%d",
                    perf_counter() - start,
                    stats.get("courses_synced", 0),
                    stats.get("assignments_synced", 0),
                )
            except Exception:
                pass

        return json.dumps(stats, indent=2)

    except Exception as e:
        if _logger:
            try:
                _logger.error("TOOL ERROR: run_context_update | error=%s", str(e))
            except Exception:
                pass
        return json.dumps({"error": f"Failed to sync context: {str(e)}"}, indent=2)


@tool
async def get_unassessed_assignments(user_id: int) -> str:
    """Get list of assignments that don't have assessments yet.

    Use this tool to:
    - Find new assignments that need assessment
    - Identify which assignments need effort estimation
    - Get assignments ready for auto-scheduling

    Args:
        user_id: Database user ID

    Returns:
        JSON array of assignments without assessments (assignment_id, title, description, due_date)
    """
    if _logger:
        try:
            _logger.info("TOOL CALL: get_unassessed_assignments | user_id=%d", user_id)
        except Exception:
            pass

    start = perf_counter()
    assignments = []

    try:
        with get_db_session() as db:
            user_assignments = db.query(UserAssignment).filter(
                UserAssignment.user_id == user_id,
                UserAssignment.status == AssignmentStatus.NOT_STARTED
            ).all()

            for ua in user_assignments:
                assignment = db.query(Assignment).filter(
                    Assignment.id == ua.assignment_id
                ).first()

                if assignment:
                    # Check if assessment exists
                    existing = db.query(AssignmentAssessment).filter(
                        AssignmentAssessment.assignment_id == assignment.id
                    ).first()

                    if not existing:
                        assignments.append({
                            "assignment_id": assignment.id,
                            "course_id": assignment.course_id,
                            "title": assignment.title,
                            "description": assignment.description_short or "",
                            "due_date": assignment.due_at.isoformat() if assignment.due_at else None,
                        })

        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: get_unassessed_assignments | duration=%.2fs | count=%d",
                    perf_counter() - start,
                    len(assignments),
                )
            except Exception:
                pass

        return json.dumps(assignments, indent=2)

    except Exception as e:
        if _logger:
            try:
                _logger.error("TOOL ERROR: get_unassessed_assignments | error=%s", str(e))
            except Exception:
                pass
        return json.dumps({"error": f"Failed to get assignments: {str(e)}"}, indent=2)
