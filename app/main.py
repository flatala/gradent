"""FastAPI backend server for the Gradent Study Assistant."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agents.chat_agent.agent import MainAgent
from agents.shared.workflow_tools import (
    assess_assignment,
    generate_suggestions,
    run_scheduler_workflow,
)
from agents.task_agents.exam_api import ExamAPIState, exam_api_graph
from agents.task_agents.progress_tracking.tools import (
    get_assignment_progress,
    get_user_study_summary,
    log_study_progress,
)
from context_updater.brightspace_client import MockBrightspaceClient
from database.connection import get_db, get_db_session
from database.models import (
    Assignment,
    AssignmentStatus,
    Course,
    Suggestion,
    SuggestionStatus,
    User,
    UserAssignment,
)
from shared.config import Configuration

# --------------------------------------------------------------------------- #
# Environment / logging setup
# --------------------------------------------------------------------------- #

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gradent.api")

# --------------------------------------------------------------------------- #
# FastAPI application & configuration
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="Gradent Study Assistant API",
    description="Unified API for chat, scheduling, suggestions, progress tracking, and exam generation.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# --------------------------------------------------------------------------- #
# Shared configuration and helpers
# --------------------------------------------------------------------------- #

AGENT_CONFIG: Optional[Configuration] = None
CONFIG_ERROR: Optional[str] = None

try:
    cfg = Configuration()
    cfg.validate()
    AGENT_CONFIG = cfg
    logger.info("Configuration loaded successfully.")
except ValueError as exc:  # pragma: no cover - configuration handled at runtime
    CONFIG_ERROR = str(exc)
    logger.warning("Configuration validation failed: %s", exc)

_CHAT_SESSIONS: Dict[str, MainAgent] = {}
_CHAT_LOCK = asyncio.Lock()


def _require_agent_config() -> Configuration:
    """Return validated configuration or raise an HTTP error."""
    if AGENT_CONFIG is None:
        raise HTTPException(
            status_code=500,
            detail=f"Configuration error: {CONFIG_ERROR or 'Missing OPENAI_API_KEY'}",
        )
    return AGENT_CONFIG


def _make_config_payload(config: Configuration) -> Dict[str, Dict[str, Any]]:
    payload = {
        "openai_api_key": config.openai_api_key,
        "openai_base_url": config.openai_base_url,
        "openai_timeout": config.openai_timeout,
        "openai_max_retries": config.openai_max_retries,
        "orchestrator_model": config.orchestrator_model,
        "text_model": config.text_model,
    }
    return {"configurable": {k: v for k, v in payload.items() if v is not None}}


def _serialize_chat_history(agent: MainAgent) -> List[Dict[str, str]]:
    """Convert chat history messages into serializable dictionaries."""
    serialized: List[Dict[str, str]] = []
    for message in agent.chat_history:
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            role = getattr(message, "type", "assistant")
        serialized.append(
            {
                "role": role,
                "content": getattr(message, "content", "") or "",
            }
        )
    return serialized


def _suggestion_to_dict(row: Suggestion) -> Dict[str, Any]:
    """Serialize a Suggestion ORM row to a dictionary."""
    return {
        "id": row.id,
        "user_id": row.user_id,
        "title": row.title,
        "message": row.message,
        "category": row.category,
        "priority": row.priority,
        "suggested_time": row.suggested_time.isoformat() if row.suggested_time else None,
        "suggested_time_text": row.suggested_time_text,
        "status": row.status.value if row.status else None,
        "channel_config": row.channel_config or {},
        "linked_assignments": row.linked_assignments or [],
        "linked_events": row.linked_events or [],
        "tags": row.tags or [],
        "sources": row.sources or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _coerce_suggestion(record: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure suggestion payload contains the fields required by SuggestionRecord."""
    defaults = {
        "id": record.get("id") or 0,
        "user_id": record.get("user_id") or 0,
        "title": record.get("title") or "",
        "message": record.get("message") or "",
        "category": record.get("category"),
        "priority": record.get("priority"),
        "suggested_time": record.get("suggested_time"),
        "suggested_time_text": record.get("suggested_time_text"),
        "status": record.get("status"),
        "channel_config": record.get("channel_config") or {},
        "linked_assignments": record.get("linked_assignments") or [],
        "linked_events": record.get("linked_events") or [],
        "tags": record.get("tags") or [],
        "sources": record.get("sources") or [],
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }
    return defaults


# --------------------------------------------------------------------------- #
# Pydantic models
# --------------------------------------------------------------------------- #


class HealthResponse(BaseModel):
    status: str
    message: str


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client-defined session identifier")
    message: str = Field(..., description="User message for the agent")
    reset: bool = Field(False, description="Reset the chat session before sending the message")


class ChatResponse(BaseModel):
    session_id: str
    response: str
    history: List[ChatHistoryMessage]


class ChatHistoryResponse(BaseModel):
    session_id: str
    history: List[ChatHistoryMessage]


class SessionsResponse(BaseModel):
    sessions: List[str]


class SuggestionRecord(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    category: Optional[str] = None
    priority: Optional[str] = None
    suggested_time: Optional[str] = None
    suggested_time_text: Optional[str] = None
    status: Optional[str] = None
    channel_config: Dict[str, Any] = Field(default_factory=dict)
    linked_assignments: List[Any] = Field(default_factory=list)
    linked_events: List[Any] = Field(default_factory=list)
    tags: List[Any] = Field(default_factory=list)
    sources: List[Any] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SuggestionListResponse(BaseModel):
    suggestions: List[SuggestionRecord]


class SuggestionsRequest(BaseModel):
    user_id: Optional[int] = Field(default=None, description="Filter suggestions for a specific user")
    status: Optional[str] = Field(default=None, description="Filter by status (pending, notified, etc.)")


class SuggestionsResetRequest(BaseModel):
    user_id: Optional[int] = Field(default=None, description="Limit reset to a specific user")
    status: Optional[str] = Field(default="pending", description="Status to apply to the suggestions")


class SuggestionsMutationResponse(BaseModel):
    success: bool
    updated: int
    message: str


class AssignmentAssessmentRequest(BaseModel):
    title: str
    description: str
    course_name: Optional[str] = "Unknown Course"
    assignment_id: Optional[int] = None


class AssignmentAssessmentResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ScheduleRequest(BaseModel):
    meeting_name: str
    duration_minutes: int
    topic: Optional[str] = None
    event_description: Optional[str] = None
    attendee_emails: Optional[List[str]] = None
    location: Optional[str] = None
    constraints: Optional[str] = None


class ScheduleResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ProgressLogRequest(BaseModel):
    user_id: int
    assignment_id: Optional[int] = None
    course_id: Optional[int] = None
    minutes: int = Field(..., gt=0)
    focus_rating: Optional[int] = Field(default=None, ge=1, le=5)
    quality_rating: Optional[int] = Field(default=None, ge=1, le=5)
    source: str = Field(default="ad_hoc", description="Origin of the study session")
    study_block_id: Optional[int] = None
    notes: Optional[str] = None


class ProgressLogResponse(BaseModel):
    success: bool
    message: str
    hours_logged: float
    study_history_id: Optional[int] = None
    assignment_progress: Optional[Dict[str, Any]] = None
    focus_rating: Optional[int] = None
    quality_rating: Optional[int] = None


class ProgressSummaryResponse(BaseModel):
    success: bool
    period_days: Optional[int] = None
    total_minutes: Optional[int] = None
    total_hours: Optional[float] = None
    total_sessions: Optional[int] = None
    assignments_worked_on: Optional[int] = None
    avg_focus: Optional[float] = None
    avg_quality: Optional[float] = None
    message: Optional[str] = None
    top_assignments: Optional[List[Dict[str, Any]]] = None


class AssignmentProgressResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    assignment_id: Optional[int] = None
    assignment_title: Optional[str] = None
    course_name: Optional[str] = None
    due_at: Optional[str] = None
    status: Optional[str] = None
    hours_done: Optional[float] = None
    hours_remaining: Optional[float] = None
    last_worked_at: Optional[str] = None
    total_sessions: Optional[int] = None
    recent_focus_avg: Optional[float] = None
    recent_quality_avg: Optional[float] = None
    priority: Optional[int] = None


class ExamResponse(BaseModel):
    success: bool
    questions: Optional[str] = None
    error: Optional[str] = None
    uploaded_files: Optional[List[str]] = None


class ExamAssessmentRequest(BaseModel):
    assignment_title: str
    course_name: str
    questions: List[Dict[str, Any]]  # Each question should have: number, text, options
    user_answers: Dict[str, str]  # question_number -> selected_answer
    correct_answers: Dict[str, str]  # question_number -> correct_answer


class ExamAssessmentResponse(BaseModel):
    success: bool
    score: Optional[int] = None
    total_questions: Optional[int] = None
    percentage: Optional[float] = None
    study_recommendation: Optional[str] = None
    detailed_feedback: Optional[str] = None
    error: Optional[str] = None


class AssignmentResponse(BaseModel):
    id: str
    title: str
    course: str
    courseName: str
    dueDate: str
    weight: float
    urgency: str
    autoSelected: bool
    topics: List[str]
    description: Optional[str] = None
    materials: Optional[str] = None


class AssignmentsListResponse(BaseModel):
    success: bool
    assignments: List[AssignmentResponse]


class SimpleStatusResponse(BaseModel):
    status: str
    message: str


# --------------------------------------------------------------------------- #
# API Routes
# --------------------------------------------------------------------------- #


@app.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """Root endpoint - health check."""
    return HealthResponse(status="ok", message="Gradent Study Assistant API is running")


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", message="Backend is operational")


# --------------------------------------------------------------------------- #
# Chat endpoints
# --------------------------------------------------------------------------- #


@app.get("/api/chat/sessions", response_model=SessionsResponse)
async def list_chat_sessions() -> SessionsResponse:
    """List active chat session identifiers."""
    async with _CHAT_LOCK:
        sessions = sorted(_CHAT_SESSIONS.keys())
    return SessionsResponse(sessions=sessions)


@app.get("/api/chat/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str) -> ChatHistoryResponse:
    """Return chat history for a specific session."""
    async with _CHAT_LOCK:
        agent = _CHAT_SESSIONS.get(session_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Session not found")
    history = [
        ChatHistoryMessage(**entry) for entry in _serialize_chat_history(agent)
    ]
    return ChatHistoryResponse(session_id=session_id, history=history)


@app.delete("/api/chat/{session_id}", response_model=SimpleStatusResponse)
async def reset_chat_session(session_id: str) -> SimpleStatusResponse:
    """Delete a chat session and its history."""
    async with _CHAT_LOCK:
        existed = _CHAT_SESSIONS.pop(session_id, None)
    if not existed:
        raise HTTPException(status_code=404, detail="Session not found")
    return SimpleStatusResponse(status="ok", message=f"Session '{session_id}' cleared.")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_agent(payload: ChatRequest) -> ChatResponse:
    """Send a message to the main agent and get a reply."""
    config = _require_agent_config()
    async with _CHAT_LOCK:
        if payload.reset and payload.session_id in _CHAT_SESSIONS:
            del _CHAT_SESSIONS[payload.session_id]
        agent = _CHAT_SESSIONS.get(payload.session_id)
        if agent is None:
            agent = MainAgent(config)
            _CHAT_SESSIONS[payload.session_id] = agent

    response_text = await agent.chat(payload.message)
    history = [
        ChatHistoryMessage(**entry) for entry in _serialize_chat_history(agent)
    ]
    return ChatResponse(session_id=payload.session_id, response=response_text, history=history)


# --------------------------------------------------------------------------- #
# Suggestions endpoints
# --------------------------------------------------------------------------- #


@app.get("/api/suggestions", response_model=SuggestionListResponse)
async def list_suggestions(params: SuggestionsRequest = SuggestionsRequest()) -> SuggestionListResponse:
    """Return persisted suggestions from the database."""
    with get_db_session() as db:
        query = db.query(Suggestion)
        if params.user_id is not None:
            query = query.filter(Suggestion.user_id == params.user_id)
        if params.status:
            try:
                status_enum = SuggestionStatus(params.status.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid suggestion status.")
            query = query.filter(Suggestion.status == status_enum)
        rows = query.order_by(Suggestion.created_at.desc()).all()
        serialized = [_suggestion_to_dict(row) for row in rows]

    records = [SuggestionRecord(**_coerce_suggestion(item)) for item in serialized]
    return SuggestionListResponse(suggestions=records)


@app.post("/api/suggestions/generate", response_model=SuggestionListResponse)
async def generate_suggestions_endpoint(payload: SuggestionsRequest) -> SuggestionListResponse:
    """Trigger the suggestions workflow and return the generated suggestions."""
    config = _require_agent_config()
    tool_input: Dict[str, Any] = {}
    if payload.user_id is not None:
        tool_input["user_id"] = payload.user_id

    result_json = await generate_suggestions.ainvoke(
        tool_input,
        config=_make_config_payload(config),
    )
    try:
        parsed = json.loads(result_json)
    except json.JSONDecodeError as exc:
        logger.error("Suggestions workflow returned invalid JSON: %s", result_json)
        raise HTTPException(
            status_code=500,
            detail=f"Suggestions workflow returned invalid data: {exc}",
        )

    if isinstance(parsed, dict) and parsed.get("error"):
        raise HTTPException(status_code=400, detail=parsed.get("error"))

    if not isinstance(parsed, list):
        parsed = [parsed]

    records = [SuggestionRecord(**_coerce_suggestion(item)) for item in parsed]
    return SuggestionListResponse(suggestions=records)


@app.post("/api/suggestions/reset", response_model=SuggestionsMutationResponse)
async def reset_suggestions(payload: SuggestionsResetRequest) -> SuggestionsMutationResponse:
    """Reset suggestion statuses (useful for demo/testing notification flows)."""
    desired_status = payload.status or "pending"
    try:
        status_enum = SuggestionStatus(desired_status.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid suggestion status.")

    with get_db_session() as db:
        query = db.query(Suggestion)
        if payload.user_id is not None:
            query = query.filter(Suggestion.user_id == payload.user_id)
        updated = 0
        now = datetime.utcnow()
        for suggestion in query:
            suggestion.status = status_enum
            suggestion.times_notified = 0
            suggestion.delivered_at = None
            suggestion.last_notified_at = None
            suggestion.updated_at = now
            updated += 1

    message = f"Updated {updated} suggestion(s) to status '{status_enum.value}'."
    return SuggestionsMutationResponse(success=True, updated=updated, message=message)


# --------------------------------------------------------------------------- #
# Assignment assessment and scheduling
# --------------------------------------------------------------------------- #


@app.post("/api/assess-assignment", response_model=AssignmentAssessmentResponse)
async def assess_assignment_endpoint(
    payload: AssignmentAssessmentRequest,
) -> AssignmentAssessmentResponse:
    """Run the assignment assessment workflow."""
    config = _require_agent_config()
    tool_input = {
        "title": payload.title,
        "description": payload.description,
        "course_name": payload.course_name,
        "assignment_id": payload.assignment_id,
    }
    result_raw = await assess_assignment.ainvoke(
        tool_input,
        config=_make_config_payload(config),
    )

    try:
        parsed = json.loads(result_raw)
    except json.JSONDecodeError:
        message = result_raw.strip()
        return AssignmentAssessmentResponse(
            success=False,
            error=message or "Assessment workflow did not return structured data.",
        )

    if isinstance(parsed, dict) and parsed.get("error"):
        return AssignmentAssessmentResponse(success=False, error=parsed["error"])

    return AssignmentAssessmentResponse(success=True, data=parsed if isinstance(parsed, dict) else {"result": parsed})


@app.post("/api/schedule", response_model=ScheduleResponse)
async def schedule_event(payload: ScheduleRequest) -> ScheduleResponse:
    """Invoke the scheduler workflow to plan an event."""
    config = _require_agent_config()
    tool_input = payload.dict(exclude_none=True)
    result = await run_scheduler_workflow.ainvoke(
        tool_input,
        config=_make_config_payload(config),
    )

    try:
        parsed = json.loads(result)
    except json.JSONDecodeError:
        logger.error("Scheduler workflow returned invalid JSON: %s", result)
        return ScheduleResponse(
            success=False,
            error="Scheduler workflow returned invalid data.",
        )

    if parsed.get("status") == "success":
        return ScheduleResponse(success=True, data=parsed)

    return ScheduleResponse(
        success=False,
        error=parsed.get("reason") or "Scheduling failed.",
        data=parsed,
    )


# --------------------------------------------------------------------------- #
# Progress tracking
# --------------------------------------------------------------------------- #


@app.post("/api/progress/log", response_model=ProgressLogResponse)
async def log_progress(payload: ProgressLogRequest) -> ProgressLogResponse:
    """Log a study session."""
    result = await asyncio.to_thread(log_study_progress, **payload.dict())
    return ProgressLogResponse(**result)


@app.get("/api/progress/summary", response_model=ProgressSummaryResponse)
async def progress_summary(user_id: int, days: int = 7) -> ProgressSummaryResponse:
    """Return a study summary for a user."""
    result = await asyncio.to_thread(get_user_study_summary, user_id, days)
    return ProgressSummaryResponse(**result)


@app.get("/api/progress/assignments/{assignment_id}", response_model=AssignmentProgressResponse)
async def assignment_progress(user_id: int, assignment_id: int) -> AssignmentProgressResponse:
    """Return detailed progress for a specific assignment."""
    result = await asyncio.to_thread(get_assignment_progress, user_id, assignment_id)
    return AssignmentProgressResponse(**result)


# --------------------------------------------------------------------------- #
# Assignment endpoints - reads from materials folder
# --------------------------------------------------------------------------- #


@app.get("/api/assignments", response_model=AssignmentsListResponse)
async def get_assignments() -> AssignmentsListResponse:
    """Get assignments based on PDF files in the materials folder."""
    db: Session = next(get_db())
    try:
        # Get PDF files from materials folder
        project_root = Path(__file__).parent.parent
        materials_dir = project_root / "materials"
        
        logger.info(f"Looking for PDFs in: {materials_dir}")
        
        if not materials_dir.exists():
            materials_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created materials directory: {materials_dir}")
        
        pdf_files = list(materials_dir.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files: {[f.name for f in pdf_files]}")
        
        if not pdf_files:
            logger.warning("No PDF files found in materials folder")
            return AssignmentsListResponse(success=True, assignments=[])
        
        # Get or create user
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(
                id=1,
                name="Test User",
                email="test@example.com",
                timezone="America/New_York"
            )
            db.add(user)
            db.commit()
            logger.info("Created test user")
        
        # Get all courses and assignments from database
        courses = db.query(Course).filter(Course.user_id == user.id).all()
        db_assignments = db.query(Assignment).join(Course).filter(Course.user_id == user.id).all()
        logger.info(f"Found {len(courses)} courses and {len(db_assignments)} assignments in database")
        
        assignments = []
        for pdf_file in pdf_files:
            # Parse filename to extract assignment info
            filename = pdf_file.stem  # filename without extension
            
            # Try to split by common separators
            parts = filename.replace('_', ' ').replace('-', ' ').split()
            
            # Extract assignment title and try to find course
            assignment_title = filename
            course_code = "UNKNOWN"
            course_name = "General Course"
            matched_course = None
            
            # First, try to find assignment in database by title match
            for db_assignment in db_assignments:
                # Check if PDF filename contains the assignment title or vice versa
                if (db_assignment.title.lower() in filename.lower() or 
                    filename.lower() in db_assignment.title.lower() or
                    # Fuzzy match - check if significant words match
                    any(word.lower() in filename.lower() for word in db_assignment.title.split() if len(word) > 4)):
                    # Found matching assignment - get its course
                    matched_course = db_assignment.course
                    course_code = matched_course.code or "COURSE"
                    course_name = matched_course.title
                    assignment_title = db_assignment.title  # Use DB title instead of filename
                    logger.info(f"Matched PDF '{pdf_file.name}' to assignment '{db_assignment.title}' in course '{course_name}'")
                    break
            
            # If no assignment match, try to match with courses directly
            if not matched_course:
                for course in courses:
                    if course.code and course.code.upper() in filename.upper():
                        matched_course = course
                        course_code = course.code
                        course_name = course.title
                        break
                    elif course.title and any(word.upper() in filename.upper() for word in course.title.split()):
                        matched_course = course
                        course_code = course.code or "COURSE"
                        course_name = course.title
                        break
            
            # If still no course found, try to extract from filename
            if not matched_course and len(parts) > 1:
                # Try to extract course code (usually uppercase letters + numbers)
                for part in parts:
                    if part.isupper() or (len(part) > 2 and any(c.isdigit() for c in part)):
                        course_code = part
                        break
            
            # Generate assignment details
            assignment = AssignmentResponse(
                id=str(abs(hash(pdf_file.name))),  # Use absolute hash of filename as ID
                title=assignment_title,
                course=course_code,
                courseName=course_name,
                dueDate=(datetime.now() + timedelta(days=14)).isoformat(),  # Default 2 weeks from now
                weight=10.0,
                urgency="medium",
                autoSelected=False,
                topics=[part for part in parts if len(part) > 3][:5],  # Use words as topics
                description=f"Study materials from {pdf_file.name}",
                materials=str(pdf_file.absolute())
            )
            assignments.append(assignment)
            logger.info(f"Created assignment: {assignment.title}")
        
        logger.info(f"Returning {len(assignments)} assignment(s)")
        return AssignmentsListResponse(success=True, assignments=assignments)
        
    except Exception as e:
        logger.error(f"Error reading assignments from materials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Exam generation endpoints
# --------------------------------------------------------------------------- #


@app.post("/api/generate-exam", response_model=ExamResponse)
async def generate_exam(
    files: Optional[List[UploadFile]] = File(None, description="PDF files to process"),
    question_header: str = Form(..., description="Exam header/title"),
    question_description: str = Form(..., description="Question requirements"),
    api_key: Optional[str] = Form(None, description="OpenRouter API key"),
    model_name: Optional[str] = Form(None, description="AI model to use"),
    use_default_pdfs: bool = Form(False, description="Use PDFs from materials folder"),
):
    """Generate exam questions from uploaded PDF files or default materials."""
    saved_paths: List[str] = []
    temp_files_to_delete: List[str] = []  # Track only temporary uploaded files
    
    try:
        # If using default PDFs, look for PDFs in the project root or materials folder
        if use_default_pdfs or not files:
            # Check for PDFs in project root
            project_root = Path(__file__).parent.parent
            pdf_files = list(project_root.glob("*.pdf"))
            
            # Also check materials folder if it exists
            materials_dir = project_root / "materials"
            if materials_dir.exists():
                pdf_files.extend(materials_dir.glob("*.pdf"))
            
            if not pdf_files:
                raise HTTPException(
                    status_code=400,
                    detail="No PDF files found in materials folder. Please upload files or add PDFs to the project.",
                )
            
            saved_paths = [str(pdf.absolute()) for pdf in pdf_files[:5]]  # Limit to 5 PDFs
            # Don't add to temp_files_to_delete - these are permanent files!
            logger.info(f"Using {len(saved_paths)} default PDF(s): {[Path(p).name for p in saved_paths]}")
        else:
            # Process uploaded files
            for file in files:
                if not file.filename.lower().endswith(".pdf"):
                    raise HTTPException(
                        status_code=400,
                        detail=f"File {file.filename} is not a PDF",
                    )
                file_path = UPLOAD_DIR / file.filename
                with file_path.open("wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                saved_paths.append(str(file_path.absolute()))
                temp_files_to_delete.append(str(file_path.absolute()))  # Only delete uploaded files
                logger.info("Saved file: %s", file_path)

        final_api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not final_api_key:
            raise HTTPException(
                status_code=400,
                detail="API key required. Provide in form or set OPENROUTER_API_KEY env variable.",
            )

        api_base_url = os.getenv("EXAM_API_BASE_URL", "http://localhost:3000")
        default_model = os.getenv("EXAM_API_MODEL", "meta-llama/llama-4-scout:free")

        state = ExamAPIState(
            pdf_paths=saved_paths,
            question_header=question_header,
            question_description=question_description,
            api_key=final_api_key,
            api_base_url=api_base_url,
            model_name=model_name or default_model,
        )

        logger.info("Starting exam generation workflow...")
        result = await exam_api_graph.ainvoke(state)

        if isinstance(result, dict):
            error = result.get("error")
            generated_questions = result.get("generated_questions")
        else:
            error = getattr(result, "error", None)
            generated_questions = getattr(result, "generated_questions", None)

        if error:
            logger.error("Exam workflow error: %s", error)
            
            # Provide more helpful error messages
            error_message = error
            if "server is busy" in error.lower() or "429" in error:
                error_message = "The AI service is currently rate-limited. Please wait 30-60 seconds and try again. Consider using a different model or upgrading to a paid tier for better availability."
            elif "rate limit" in error.lower():
                error_message = "Rate limit exceeded. Please wait a few minutes before trying again."
            
            return ExamResponse(success=False, error=error_message)

        if not generated_questions:
            logger.warning("No questions were generated by the workflow.")
            return ExamResponse(
                success=False,
                error="No questions were generated. Please check your input.",
            )

        # Remove everything after "**Section B: Answers**"
        logger.info("Applying answer section cutoff...")
        output = generated_questions.split("**Section B: Answers**")[0].strip()
        logger.info(f"Original length: {len(generated_questions)}, After cutoff: {len(output)}")
        
        logger.info("Exam generation completed successfully.")
        return ExamResponse(
            success=True,
            questions=output,
            uploaded_files=[Path(path).name for path in saved_paths],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error during exam generation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        # Only delete temporary uploaded files, NOT materials folder files
        for path in temp_files_to_delete:
            try:
                Path(path).unlink()
                logger.info(f"Deleted temporary file: {path}")
            except FileNotFoundError:
                continue
            except Exception as exc:  # pragma: no cover - best effort cleanup
                logger.warning("Failed to delete temporary file %s: %s", path, exc)


@app.post("/api/assess-exam", response_model=ExamAssessmentResponse)
async def assess_exam(request: ExamAssessmentRequest) -> ExamAssessmentResponse:
    """
    Assess a completed exam using OpenAI to analyze performance and provide
    personalized study recommendations. Saves results to database for scheduler integration.
    """
    try:
        # Get configuration and LLM
        config = Configuration()
        config.validate()
        
        from shared.utils import get_text_llm
        llm = get_text_llm(config)
        
        # Calculate score
        total_questions = len(request.questions)
        correct_count = 0
        
        for q_id, user_answer in request.user_answers.items():
            correct_answer = request.correct_answers.get(q_id, "")
            if user_answer.strip().upper() == correct_answer.strip().upper():
                correct_count += 1
        
        percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        # Build detailed context for the LLM
        questions_text = "\n\n".join([
            f"Question {i+1}: {q.get('text', q.get('question', 'N/A'))}\n"
            f"Options: {', '.join([f'{opt}' for opt in q.get('options', [])])}\n"
            f"Correct Answer: {request.correct_answers.get(str(i+1), 'N/A')}\n"
            f"User Answer: {request.user_answers.get(str(i+1), 'Not answered')}"
            for i, q in enumerate(request.questions)
        ])
        
        # Create prompt for LLM with specific hour extraction instructions
        prompt = f"""You are an educational assessment expert. A student has just completed a mock exam for the following assignment:

**Course**: {request.course_name}
**Assignment**: {request.assignment_title}

**Exam Results**:
- Score: {correct_count}/{total_questions} ({percentage:.1f}%)

**Detailed Questions and Answers**:
{questions_text}

Based on this performance, provide a study time recommendation in the following format:

**Study Time Recommendation:** [X-Y hours] or [X hours]

Then provide brief, actionable feedback on:
- What topics/concepts they understand well
- What areas need more focus
- Specific study strategies

Be concise and encouraging. Start with the exact hours needed (e.g., "2-3 hours", "4-5 hours", "1-2 hours") based on the score:
- 90-100%: 1-2 hours (review and consolidation)
- 70-89%: 2-4 hours (targeted practice on weak areas)
- 50-69%: 4-6 hours (substantial study needed)
- Below 50%: 6-8 hours (comprehensive review required)"""

        # Call LLM
        logger.info(f"Sending exam assessment to LLM for {request.assignment_title}")
        
        messages = [
            ("system", "You are an educational assessment expert who provides personalized study recommendations based on exam performance."),
            ("human", prompt)
        ]
        
        response = await llm.ainvoke(messages)
        ai_feedback = response.content if hasattr(response, 'content') else str(response)
        
        # Extract study recommendation and hours
        lines = ai_feedback.split('\n')
        study_rec = "Based on your performance, review the material for 2-3 hours focusing on weak areas."
        study_hours = None
        
        # Try to find the study time recommendation section and extract hours
        import re
        for i, line in enumerate(lines):
            if "study time" in line.lower() or "hours" in line.lower():
                # Get the next few lines as the recommendation
                study_rec = '\n'.join(lines[i:min(i+3, len(lines))]).strip()
                # Extract numeric hours (e.g., "2-3 hours" -> 2.5, "4 hours" -> 4)
                hours_match = re.search(r'(\d+)(?:-(\d+))?\s*hours?', line.lower())
                if hours_match:
                    low = float(hours_match.group(1))
                    high = float(hours_match.group(2)) if hours_match.group(2) else low
                    study_hours = (low + high) / 2
                break
        
        # Fallback: estimate hours based on percentage if not extracted
        if study_hours is None:
            if percentage >= 90:
                study_hours = 1.5
            elif percentage >= 70:
                study_hours = 3.0
            elif percentage >= 50:
                study_hours = 5.0
            else:
                study_hours = 7.0
        
        logger.info(f"Assessment completed: {correct_count}/{total_questions} correct, recommended hours: {study_hours}")
        
        # Save exam result to database
        try:
            from database.models import ExamResult, Assignment, UserAssignment
            
            db: Session = next(get_db())
            
            # Find the assignment by title and course (assuming user_id=1 for now)
            assignment = db.query(Assignment).join(Assignment.course).filter(
                Assignment.title == request.assignment_title,
            ).first()
            
            if assignment:
                # Save exam result
                exam_result = ExamResult(
                    user_id=1,  # TODO: Get from authenticated user session
                    assignment_id=assignment.id,
                    exam_type='multiple-choice' if any(q.get('options') for q in request.questions) else 'open-ended',
                    total_questions=total_questions,
                    score=correct_count,
                    percentage=percentage,
                    study_hours_recommended=study_hours,
                    study_recommendation_text=study_rec,
                    questions=[{
                        'number': q.get('number'),
                        'text': q.get('text', q.get('question')),
                        'options': q.get('options', [])
                    } for q in request.questions],
                    user_answers=request.user_answers,
                    correct_answers=request.correct_answers,
                )
                
                db.add(exam_result)
                db.commit()
                logger.info(f"Saved exam result to database (ID: {exam_result.id})")
                
                # Update UserAssignment with exam-based time estimate
                user_assignment = db.query(UserAssignment).filter(
                    UserAssignment.user_id == 1,  # TODO: Get from authenticated user session
                    UserAssignment.assignment_id == assignment.id
                ).first()
                
                if user_assignment:
                    # Update hours remaining based on exam performance
                    user_assignment.hours_remaining = study_hours
                    user_assignment.hours_estimated_user = study_hours  # Mark as user-influenced (exam-based)
                    db.commit()
                    logger.info(f"Updated UserAssignment hours_remaining to {study_hours} hours based on exam performance")
                else:
                    # Create UserAssignment if it doesn't exist
                    user_assignment = UserAssignment(
                        user_id=1,
                        assignment_id=assignment.id,
                        hours_estimated_user=study_hours,
                        hours_remaining=study_hours,
                        status=AssignmentStatus.IN_PROGRESS
                    )
                    db.add(user_assignment)
                    db.commit()
                    logger.info(f"Created UserAssignment with {study_hours} hours based on exam performance")
                
            else:
                logger.warning(f"Could not find assignment '{request.assignment_title}' to link exam result")
        except Exception as db_error:
            logger.error(f"Failed to save exam result to database: {db_error}", exc_info=True)
            # Don't fail the entire request if DB save fails
        
        return ExamAssessmentResponse(
            success=True,
            score=correct_count,
            total_questions=total_questions,
            percentage=round(percentage, 1),
            study_recommendation=study_rec,
            detailed_feedback=ai_feedback,
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error assessing exam: {exc}", exc_info=True)
        return ExamAssessmentResponse(
            success=False,
            error=f"Failed to assess exam: {str(exc)}",
        )


@app.delete("/api/cleanup", response_model=SimpleStatusResponse)
async def cleanup_uploads() -> SimpleStatusResponse:
    """Clean up all uploaded files (for testing)."""
    count = 0
    for file_path in UPLOAD_DIR.glob("*"):
        if file_path.is_file():
            file_path.unlink()
            count += 1
    return SimpleStatusResponse(
        status="ok",
        message=f"Cleaned up {count} file(s)",
    )


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Starting Gradent Study Assistant Backend Server")
    print("=" * 60)
    print("Server will be available at: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
