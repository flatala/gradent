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
    Assignment,
    UserAssignment,
    AssignmentStatus,
    AssignmentAssessment,
)
from agents.task_agents.scheduler import scheduler_graph, SchedulerState
from agents.task_agents.assignment_assessment import assessment_graph, AssessmentState, AssignmentInfo
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
        constraints: IMPORTANT: Include specific day/date information here!
                    Examples:
                    - 'on Wednesday' or 'on Friday'
                    - 'on Monday and Thursday'
                    - 'next week' or 'tomorrow'
                    - 'mornings only', 'after 2pm', 'avoid Mondays'
                    If the user mentions a specific day like "Wednesday" or "Friday",
                    YOU MUST include it in the constraints parameter!
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
        time_constraints=constraints,  # Fixed: was 'constraints', should be 'time_constraints'
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


@tool
async def get_user_assignments(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    course_id: Optional[int] = None,
    include_details: bool = True,
) -> str:
    """Get information about user's assignments with filtering options.

    Use this tool when the user asks about:
    - Their assignments or homework
    - What they need to do
    - Assignments for a specific course
    - Completed or in-progress work
    - Assignment details, deadlines, or status

    Args:
        user_id: Database user ID (defaults to 1)
        status: Filter by status - 'not_started', 'in_progress', or 'done' (optional)
        course_id: Filter by specific course ID (optional)
        include_details: Include assessment data and progress details (default: True)

    Returns:
        JSON array of assignments with title, course, due date, status, progress, and assessment
    """
    resolved_user_id = _resolve_user_id(user_id)
    
    if _logger:
        try:
            _logger.info(
                "TOOL CALL: get_user_assignments | user_id=%d | status=%s | course_id=%s",
                resolved_user_id, status or "all", course_id or "all"
            )
        except Exception:
            pass

    start = perf_counter()
    assignments = []

    try:
        with get_db_session() as db:
            from database.models import Course
            
            # Build query
            query = db.query(UserAssignment).filter(
                UserAssignment.user_id == resolved_user_id,
                UserAssignment.is_archived.is_(False)
            )
            
            # Apply filters
            if status:
                try:
                    status_enum = AssignmentStatus(status)
                    query = query.filter(UserAssignment.status == status_enum)
                except ValueError:
                    return json.dumps({"error": f"Invalid status: {status}. Use 'not_started', 'in_progress', or 'done'"}, indent=2)
            
            if course_id:
                query = query.join(Assignment).filter(Assignment.course_id == course_id)
            
            user_assignments = query.all()

            for ua in user_assignments:
                assignment = db.query(Assignment).filter(
                    Assignment.id == ua.assignment_id
                ).first()

                if not assignment:
                    continue
                
                # Get course info
                course = db.query(Course).filter(Course.id == assignment.course_id).first()
                
                # Build basic assignment data
                assignment_data = {
                    "assignment_id": assignment.id,
                    "user_assignment_id": ua.id,
                    "title": assignment.title,
                    "description": assignment.description_short or "",
                    "course": {
                        "id": course.id,
                        "title": course.title,
                        "code": course.code,
                        "term": course.term,
                    } if course else None,
                    "due_date": assignment.due_at.isoformat() if assignment.due_at else None,
                    "lms_link": assignment.lms_link,
                    "weight_percentage": assignment.weight_percentage,
                    "max_points": assignment.max_points,
                    "status": ua.status.value,
                    "hours_done": ua.hours_done,
                    "hours_remaining": ua.hours_remaining,
                    "last_worked_at": ua.last_worked_at.isoformat() if ua.last_worked_at else None,
                    "priority": ua.priority,
                    "notes": ua.notes,
                }
                
                # Include assessment details if requested
                if include_details:
                    assessment = db.query(AssignmentAssessment).filter(
                        AssignmentAssessment.assignment_id == assignment.id,
                        AssignmentAssessment.is_latest.is_(True)
                    ).first()
                    
                    if assessment:
                        assignment_data["assessment"] = {
                            "effort_hours_low": assessment.effort_hours_low,
                            "effort_hours_most": assessment.effort_hours_most,
                            "effort_hours_high": assessment.effort_hours_high,
                            "difficulty_1to5": assessment.difficulty_1to5,
                            "risk_score_0to100": assessment.risk_score_0to100,
                            "milestones": assessment.milestones,
                            "prerequisites": assessment.prereq_topics,
                            "deliverables": assessment.deliverables,
                        }
                    else:
                        assignment_data["assessment"] = None
                
                assignments.append(assignment_data)

        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: get_user_assignments | duration=%.2fs | count=%d",
                    perf_counter() - start,
                    len(assignments),
                )
            except Exception:
                pass

        return json.dumps(assignments, indent=2)

    except Exception as e:
        if _logger:
            try:
                _logger.error("TOOL ERROR: get_user_assignments | error=%s", str(e))
            except Exception:
                pass
        return json.dumps({"error": f"Failed to get assignments: {str(e)}"}, indent=2)


@tool
async def get_user_courses(user_id: Optional[int] = None) -> str:
    """Get information about user's courses.

    Use this tool when the user asks about:
    - Their courses or classes
    - What courses they're enrolled in
    - Course details or information
    - How many courses they have

    Args:
        user_id: Database user ID (defaults to 1)

    Returns:
        JSON array of courses with title, code, term, and assignment counts
    """
    resolved_user_id = _resolve_user_id(user_id)
    
    if _logger:
        try:
            _logger.info("TOOL CALL: get_user_courses | user_id=%d", resolved_user_id)
        except Exception:
            pass

    start = perf_counter()
    courses = []

    try:
        with get_db_session() as db:
            from database.models import Course
            from sqlalchemy import func
            
            # Get courses with assignment counts
            course_data = db.query(
                Course,
                func.count(Assignment.id).label('assignment_count')
            ).outerjoin(Assignment).filter(
                Course.user_id == resolved_user_id
            ).group_by(Course.id).all()

            for course, assignment_count in course_data:
                # Get active assignment counts by status
                active_assignments = db.query(func.count(UserAssignment.id)).join(
                    Assignment
                ).filter(
                    Assignment.course_id == course.id,
                    UserAssignment.user_id == resolved_user_id,
                    UserAssignment.is_archived.is_(False)
                ).scalar()
                
                completed_assignments = db.query(func.count(UserAssignment.id)).join(
                    Assignment
                ).filter(
                    Assignment.course_id == course.id,
                    UserAssignment.user_id == resolved_user_id,
                    UserAssignment.status == AssignmentStatus.DONE
                ).scalar()

                courses.append({
                    "course_id": course.id,
                    "title": course.title,
                    "code": course.code,
                    "term": course.term,
                    "lms_course_id": course.lms_course_id,
                    "total_assignments": assignment_count,
                    "active_assignments": active_assignments or 0,
                    "completed_assignments": completed_assignments or 0,
                    "created_at": course.created_at.isoformat() if course.created_at else None,
                })

        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: get_user_courses | duration=%.2fs | count=%d",
                    perf_counter() - start,
                    len(courses),
                )
            except Exception:
                pass

        return json.dumps(courses, indent=2)

    except Exception as e:
        if _logger:
            try:
                _logger.error("TOOL ERROR: get_user_courses | error=%s", str(e))
            except Exception:
                pass
        return json.dumps({"error": f"Failed to get courses: {str(e)}"}, indent=2)


@tool
async def get_assignment_assessment(
    assignment_id: int,
    user_id: Optional[int] = None,
) -> str:
    """Get the AI-generated assessment for a specific assignment.

    Use this tool when the user asks about:
    - How long an assignment will take
    - How difficult an assignment is
    - What milestones or subtasks an assignment has
    - Prerequisites needed for an assignment
    - Risk level or challenges of an assignment

    Args:
        assignment_id: Database assignment ID
        user_id: Database user ID (defaults to 1, used for context)

    Returns:
        JSON with assessment details including effort, difficulty, milestones, and prerequisites
    """
    resolved_user_id = _resolve_user_id(user_id)
    
    if _logger:
        try:
            _logger.info(
                "TOOL CALL: get_assignment_assessment | user_id=%d | assignment_id=%d",
                resolved_user_id, assignment_id
            )
        except Exception:
            pass

    start = perf_counter()

    try:
        with get_db_session() as db:
            from database.models import Course
            
            # Get assignment
            assignment = db.query(Assignment).filter(
                Assignment.id == assignment_id
            ).first()
            
            if not assignment:
                return json.dumps({"error": f"Assignment with ID {assignment_id} not found"}, indent=2)
            
            # Get course info
            course = db.query(Course).filter(Course.id == assignment.course_id).first()
            
            # Get latest assessment
            assessment = db.query(AssignmentAssessment).filter(
                AssignmentAssessment.assignment_id == assignment_id,
                AssignmentAssessment.is_latest.is_(True)
            ).first()
            
            if not assessment:
                return json.dumps({
                    "assignment_id": assignment_id,
                    "title": assignment.title,
                    "course": course.title if course else None,
                    "assessment": None,
                    "message": "No assessment available for this assignment. Use assess_assignment tool to generate one."
                }, indent=2)
            
            result = {
                "assignment_id": assignment_id,
                "title": assignment.title,
                "course": {
                    "id": course.id,
                    "title": course.title,
                    "code": course.code,
                } if course else None,
                "due_date": assignment.due_at.isoformat() if assignment.due_at else None,
                "assessment": {
                    "effort_estimates": {
                        "low_hours": assessment.effort_hours_low,
                        "most_likely_hours": assessment.effort_hours_most,
                        "high_hours": assessment.effort_hours_high,
                    },
                    "difficulty_1to5": assessment.difficulty_1to5,
                    "risk_score_0to100": assessment.risk_score_0to100,
                    "confidence": assessment.confidence_0to1,
                    "weight_in_course": assessment.weight_in_course,
                    "milestones": assessment.milestones,
                    "prerequisites": assessment.prereq_topics,
                    "deliverables": assessment.deliverables,
                    "blocking_dependencies": assessment.blocking_dependencies,
                    "assessed_at": assessment.created_at.isoformat() if assessment.created_at else None,
                    "version": assessment.version,
                }
            }

        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: get_assignment_assessment | duration=%.2fs | has_assessment=%s",
                    perf_counter() - start,
                    assessment is not None
                )
            except Exception:
                pass

        return json.dumps(result, indent=2)

    except Exception as e:
        if _logger:
            try:
                _logger.error("TOOL ERROR: get_assignment_assessment | error=%s", str(e))
            except Exception:
                pass
        return json.dumps({"error": f"Failed to get assessment: {str(e)}"}, indent=2)


@tool
async def get_study_progress(
    user_id: Optional[int] = None,
    assignment_id: Optional[int] = None,
    days: Optional[int] = 7,
) -> str:
    """Get study progress and history for a user or specific assignment.

    Use this tool when the user asks about:
    - How much they've studied
    - Their study history or progress
    - Time spent on an assignment
    - Recent study sessions
    - Study statistics or analytics

    Args:
        user_id: Database user ID (defaults to 1)
        assignment_id: Filter by specific assignment (optional)
        days: Number of days to look back (default: 7)

    Returns:
        JSON with study statistics and recent sessions
    """
    resolved_user_id = _resolve_user_id(user_id)
    
    if _logger:
        try:
            _logger.info(
                "TOOL CALL: get_study_progress | user_id=%d | assignment_id=%s | days=%d",
                resolved_user_id, assignment_id or "all", days
            )
        except Exception:
            pass

    start = perf_counter()

    try:
        with get_db_session() as db:
            from database.models import StudyHistory, Course
            from datetime import timedelta
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Build query for study history
            query = db.query(StudyHistory).filter(
                StudyHistory.user_id == resolved_user_id,
                StudyHistory.date >= cutoff_date
            )
            
            if assignment_id:
                # Get user_assignment_id
                ua = db.query(UserAssignment).filter(
                    UserAssignment.user_id == resolved_user_id,
                    UserAssignment.assignment_id == assignment_id
                ).first()
                
                if ua:
                    query = query.filter(StudyHistory.user_assignment_id == ua.id)
                else:
                    return json.dumps({
                        "error": f"No user assignment found for assignment_id {assignment_id}"
                    }, indent=2)
            
            # Get all study sessions
            sessions = query.order_by(StudyHistory.date.desc()).all()
            
            # Calculate statistics
            total_minutes = sum(s.minutes for s in sessions)
            total_hours = total_minutes / 60.0
            
            # Get average ratings
            focus_ratings = [s.focus_rating_1to5 for s in sessions if s.focus_rating_1to5]
            quality_ratings = [s.quality_rating_1to5 for s in sessions if s.quality_rating_1to5]
            
            avg_focus = sum(focus_ratings) / len(focus_ratings) if focus_ratings else None
            avg_quality = sum(quality_ratings) / len(quality_ratings) if quality_ratings else None
            
            # Build session details
            session_details = []
            for session in sessions[:20]:  # Limit to most recent 20
                # Get assignment/course info
                assignment_info = None
                if session.user_assignment_id:
                    ua = db.query(UserAssignment).filter(
                        UserAssignment.id == session.user_assignment_id
                    ).first()
                    if ua:
                        assignment = db.query(Assignment).filter(
                            Assignment.id == ua.assignment_id
                        ).first()
                        if assignment:
                            course = db.query(Course).filter(
                                Course.id == assignment.course_id
                            ).first()
                            assignment_info = {
                                "assignment_id": assignment.id,
                                "title": assignment.title,
                                "course": course.title if course else None,
                            }
                
                session_details.append({
                    "date": session.date.isoformat(),
                    "minutes": session.minutes,
                    "hours": round(session.minutes / 60.0, 2),
                    "assignment": assignment_info,
                    "focus_rating": session.focus_rating_1to5,
                    "quality_rating": session.quality_rating_1to5,
                    "source": session.source,
                    "notes": session.notes,
                })
            
            result = {
                "user_id": resolved_user_id,
                "period_days": days,
                "statistics": {
                    "total_sessions": len(sessions),
                    "total_minutes": total_minutes,
                    "total_hours": round(total_hours, 2),
                    "average_session_minutes": round(total_minutes / len(sessions), 1) if sessions else 0,
                    "average_focus_rating": round(avg_focus, 2) if avg_focus else None,
                    "average_quality_rating": round(avg_quality, 2) if avg_quality else None,
                },
                "recent_sessions": session_details,
            }
            
            if assignment_id:
                result["filtered_by_assignment_id"] = assignment_id

        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: get_study_progress | duration=%.2fs | sessions=%d | total_hours=%.1f",
                    perf_counter() - start,
                    len(sessions),
                    total_hours
                )
            except Exception:
                pass

        return json.dumps(result, indent=2)

    except Exception as e:
        if _logger:
            try:
                _logger.error("TOOL ERROR: get_study_progress | error=%s", str(e))
            except Exception:
                pass
        return json.dumps({"error": f"Failed to get study progress: {str(e)}"}, indent=2)
