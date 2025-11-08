"\"\"\"Nodes for the suggestions workflow.\"\"\""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from database.connection import get_db_session
from database.models import (
    Assignment,
    AssignmentAssessment,
    AssignmentStatus,
    Course,
    StudyHistory,
    UserAssignment,
)
from shared.config import Configuration
from shared.utils import get_text_llm
from vector_db.mock_documents import get_all_mock_assignments

from .prompts import (
    SUGGESTIONS_INSTRUCTION_PROMPT,
    SUGGESTIONS_SYSTEM_PROMPT,
)
from .state import SuggestionsState, Suggestion


def _serialize_assignments(state: SuggestionsState) -> Dict[str, list]:
    """Fetch and bucket assignments with optional assessments."""
    window_soon = datetime.utcnow() + timedelta(days=7)
    results: Dict[str, list] = {
        "overdue": [],
        "due_soon": [],
        "later": [],
    }
    with get_db_session() as db:
        assignment_rows = (
            db.query(Assignment, UserAssignment)
            .join(UserAssignment, UserAssignment.assignment_id == Assignment.id)
            .filter(UserAssignment.user_id == state.user_id)
            .all()
        )

        assessments = {
            ass.assignment_id: ass
            for ass in (
                db.query(AssignmentAssessment)
                .filter(
                    AssignmentAssessment.assignment_id.in_(
                        [assignment.id for assignment, _ in assignment_rows]
                    ),
                    AssignmentAssessment.is_latest.is_(True),
                )
                .all()
            )
        }

        for assignment, user_assignment in assignment_rows:
            due_at = assignment.due_at
            status_enum = (
                user_assignment.status
                if user_assignment and user_assignment.status
                else AssignmentStatus.NOT_STARTED
            )
            status = status_enum.value
            assessment = assessments.get(assignment.id)
            payload = {
                "id": assignment.id,
                "course_id": assignment.course_id,
                "title": assignment.title,
                "due_at": due_at.isoformat() if due_at else None,
                "status": status,
                "estimated_hours_user": user_assignment.hours_estimated_user
                if user_assignment
                else None,
                "hours_done": user_assignment.hours_done if user_assignment else 0.0,
                "course_title": assignment.course.title if assignment.course else None,
                "assessment": {
                    "effort_hours_low": assessment.effort_hours_low if assessment else None,
                    "effort_hours_most": assessment.effort_hours_most if assessment else None,
                    "effort_hours_high": assessment.effort_hours_high if assessment else None,
                    "difficulty_1to5": assessment.difficulty_1to5 if assessment else None,
                    "risk_score_0to100": assessment.risk_score_0to100 if assessment else None,
                    "milestones": assessment.milestones if assessment else [],
                    "deliverables": assessment.deliverables if assessment else [],
                },
            }

            if due_at and due_at < datetime.utcnow():
                results["overdue"].append(payload)
            elif due_at and due_at <= window_soon:
                results["due_soon"].append(payload)
            else:
                results["later"].append(payload)
    return results


def _mock_calendar_gaps(state: SuggestionsState) -> list:
    """Placeholder calendar block detection. Replace with real calendar data when available."""
    # For now we return an empty list; future implementation can pull from a calendar table.
    return []


def _load_study_history(state: SuggestionsState, limit: int = 20) -> List[dict]:
    """Return recent study history entries for the user."""
    with get_db_session() as db:
        rows = (
            db.query(
                StudyHistory,
                UserAssignment,
                Assignment,
                Course,
            )
            .outerjoin(UserAssignment, StudyHistory.user_assignment_id == UserAssignment.id)
            .outerjoin(Assignment, UserAssignment.assignment_id == Assignment.id)
            .outerjoin(Course, Assignment.course_id == Course.id)
            .filter(StudyHistory.user_id == state.user_id)
            .order_by(StudyHistory.date.desc())
            .limit(limit)
            .all()
        )

        history: List[dict] = []
        for history_entry, user_assignment, assignment, course in rows:
            history.append(
                {
                    "id": history_entry.id,
                    "date": history_entry.date.isoformat() if history_entry.date else None,
                    "minutes": history_entry.minutes,
                    "source": history_entry.source,
                    "focus_rating_1to5": history_entry.focus_rating_1to5,
                    "quality_rating_1to5": history_entry.quality_rating_1to5,
                    "notes": history_entry.notes,
                    "assignment": {
                        "user_assignment_id": user_assignment.id if user_assignment else None,
                        "assignment_id": assignment.id if assignment else None,
                        "title": assignment.title if assignment else None,
                    },
                    "course": {
                        "course_id": course.id if course else None,
                        "title": course.title if course else None,
                    },
                    "study_block_id": history_entry.study_block_id,
                }
            )
    return history


def _resource_matches(assignments_bucket: Dict[str, list]) -> list:
    """Link mock assignment documents to upcoming assignments."""
    docs = get_all_mock_assignments()
    title_to_key = {doc["title"]: key for key, doc in docs.items()}
    resources = []
    for bucket in assignments_bucket.values():
        for assignment in bucket:
            key = title_to_key.get(assignment["title"])
            if key:
                doc = docs[key]
                resources.append(
                    {
                        "assignment_id": assignment["id"],
                        "title": doc.get("title"),
                        "course": doc.get("course"),
                        "doc_id": key,
                        "summary": doc.get("content", "")[:500],
                    }
                )
    return resources


async def collect_context(
    state: SuggestionsState,
    *,
    config: Optional[RunnableConfig] = None,
) -> Dict:
    """Gather assignments, calendar events, study history, and new resources."""
    assignments_bucket = _serialize_assignments(state)
    calendar_events = _mock_calendar_gaps(state)
    study_history = _load_study_history(state)
    resources = _resource_matches(assignments_bucket)

    return {
        "assignments": assignments_bucket,
        "calendar_events": calendar_events,
        "study_history": study_history,
        "new_resources": resources,
    }


async def summarize_context(
    state: SuggestionsState,
    *,
    config: Optional[RunnableConfig] = None,
) -> Dict:
    """Populate the state with fetched context."""
    context = await collect_context(state, config=config)
    return {
        "assignments": context["assignments"],
        "calendar_events": context["calendar_events"],
        "study_history": context["study_history"],
        "new_resources": context["new_resources"],
    }


async def generate_suggestions_node(
    state: SuggestionsState,
    *,
    config: Optional[RunnableConfig] = None,
) -> Dict:
    """Run the LLM to produce structured suggestions."""
    cfg = Configuration.from_runnable_config(config)
    llm = get_text_llm(cfg)

    system = SystemMessage(content=SUGGESTIONS_SYSTEM_PROMPT)
    human = HumanMessage(
        content=SUGGESTIONS_INSTRUCTION_PROMPT.format(
            user_id=state.user_id,
            snapshot_ts=state.snapshot_ts.isoformat(),
            assignments_json=json.dumps(state.assignments, indent=2, default=str),
            calendar_events_json=json.dumps(state.calendar_events, indent=2, default=str),
            study_history_json=json.dumps(state.study_history, indent=2, default=str),
            resources_json=json.dumps(state.new_resources, indent=2, default=str),
        )
    )

    response = await llm.ainvoke([system, human])
    content = response.content or ""

    if "```" in content:
        # strip markdown fences if present
        content = content.split("```json")[-1] if "```json" in content else content.split("```")[-1]
        content = content.strip("`\n ")

    try:
        suggestions_raw = json.loads(content)
        if not isinstance(suggestions_raw, list):
            raise ValueError("Response is not a list of suggestions")
        suggestions = [Suggestion(**item) for item in suggestions_raw]
    except Exception as exc:  # pragma: no cover - fallback path
        fallback = [
            Suggestion(
                title="No actionable suggestions",
                message=f"Unable to parse AI suggestions: {exc}. Please retry.",
                category="other",
                priority="low",
                suggested_time=None,
            )
        ]
        suggestions = fallback

    return {"messages": [response], "suggestions": suggestions}

