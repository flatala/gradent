"""Tools that invoke workflow subgraphs."""
from __future__ import annotations
import json
import logging
import os
import time
from datetime import datetime
from time import perf_counter
from typing import Annotated, Optional

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from database.connection import get_db_session
from database.models import (
    Suggestion,
    SuggestionStatus,
    User,
)
from shared.config import Configuration
from shared.utils import get_text_llm
from workflows.assignment_assessment import (
    AssessmentState,
    AssignmentInfo,
    assessment_graph,
)
from workflows.planning import PlanningState, planning_graph, prompts
from workflows.suggestions import SuggestionsState, Suggestion as WorkflowSuggestion, suggestions_graph

_logger = logging.getLogger("chat")


@tool
async def run_planning_workflow(
    query: str,
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Execute the planning workflow to create a structured plan.

    Use this tool when the user asks you to:
    - Create a plan or strategy
    - Break down a complex goal into steps
    - Research and plan a project
    - Organize tasks or activities

    The planning workflow can search the web for information and ask the user
    for clarification if needed.

    Args:
        query: The planning request or goal to create a plan for
        config: Injected configuration (automatically provided)

    Returns:
        A structured plan with steps and considerations (as JSON string)
    """
    cfg = Configuration.from_runnable_config(config)
    if _logger:
        try:
            _logger.info("TOOL CALL: run_planning_workflow | query=%s", (query[:200] + "...") if len(query) > 200 else query)
        except Exception:
            pass

    start = perf_counter()

    # Create initial state (no human-in-the-loop interrupts)
    initial_state = PlanningState(query=query)

    # Simple retry loop to handle transient backend errors (e.g., 503)
    max_attempts = int(os.getenv("PLANNING_RETRIES", "2"))
    backoff = float(os.getenv("PLANNING_BACKOFF", "2.0"))
    last_exc: Exception | None = None
    result = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = await planning_graph.ainvoke(initial_state, config)
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

    # Workflow completed successfully
    if result.get("plan"):
        plan = result["plan"]
        if _logger:
            try:
                steps_count = len(getattr(plan, "steps", []) or [])
                _logger.info(
                    "TOOL DONE: run_planning_workflow | status=ok | duration=%.2fs | steps=%d",
                    perf_counter() - start,
                    steps_count,
                )
            except Exception:
                pass
        return json.dumps({
            "goal": plan.goal,
            "steps": plan.steps,
            "considerations": plan.considerations,
        }, indent=2)

    # If we get here, something unexpected happened
    if _logger:
        try:
            _logger.info(
                "TOOL DONE: run_planning_workflow | status=error | duration=%.2fs",
                perf_counter() - start,
            )
        except Exception:
            pass
    if last_exc:
        return f"Planning failed due to backend error: {last_exc}"
    return "Planning workflow completed but no plan was generated."


@tool
async def assess_assignment(
    title: str,
    description: str,
    course_name: str = "Unknown Course",
    assignment_id: int = None,
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
        config: Injected configuration (automatically provided)

    Returns:
        Structured assessment with effort estimates, milestones, and breakdown (as JSON string)
    """
    cfg = Configuration.from_runnable_config(config)
    if _logger:
        try:
            _logger.info("TOOL CALL: assess_assignment | title=%s | course=%s", title, course_name)
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
    
    initial_state = AssessmentState(assignment_info=assignment_info)
    
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


def _resolve_user_id(user_id: Optional[int]) -> Optional[int]:
    """Return a valid user id, defaulting to the first user in the DB."""
    if user_id is not None:
        return user_id
    with get_db_session() as db:
        record = db.query(User.id).order_by(User.id.asc()).first()
        return record[0] if record else None


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
                "chainlit": True,
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
        user_id: Target user (defaults to the first user in the database)
        config: Injected LangChain runnable configuration

    Returns:
        JSON array of suggestions with category, priority, and references.
    """
    cfg = Configuration.from_runnable_config(config)
    resolved_user_id = _resolve_user_id(user_id)
    if resolved_user_id is None:
        return json.dumps({
            "error": "No user found in database. Populate the DB before requesting suggestions."
        }, indent=2)

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
