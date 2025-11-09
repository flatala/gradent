"""FastAPI backend server for the Gradent Study Assistant."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.callbacks import BaseCallbackHandler
from pydantic import BaseModel, Field

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
from database.connection import get_db_session
from database.models import Suggestion, SuggestionStatus
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
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
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


class ToolCallTracker(BaseCallbackHandler):
    """Callback handler to track tool calls during agent execution.
    
    ONLY tracks top-level workflow tools, ignoring internal tool calls within subgraphs.
    """
    
    def __init__(self):
        self.tool_calls: List[Dict[str, Any]] = []
        # Only track these top-level workflow tools
        self.tracked_tools = {
            "run_scheduler_workflow",
            "assess_assignment", 
            "generate_suggestions",
            "run_exam_api_workflow",
            "log_progress_update",
            "run_context_update",
        }
        self.tool_map = {
            "run_scheduler_workflow": {"type": "scheduler", "name": "Schedule Meeting"},
            "assess_assignment": {"type": "assessment", "name": "Assess Assignment"},
            "generate_suggestions": {"type": "suggestions", "name": "Generate Suggestions"},
            "run_exam_api_workflow": {"type": "exam_generation", "name": "Generate Exam"},
            "log_progress_update": {"type": "progress_tracking", "name": "Log Study Progress"},
            "run_context_update": {"type": "context_update", "name": "Update Course Context"},
        }
        self.active_tool: Optional[str] = None
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Called when a tool starts executing. Only track top-level workflow tools."""
        tool_name = serialized.get("name", "unknown")
        
        # CRITICAL: Only track top-level workflow tools, ignore internal tools
        if tool_name not in self.tracked_tools:
            logger.debug(f"Ignoring internal tool call: {tool_name}")
            return
            
        tool_info = self.tool_map[tool_name]
        self.active_tool = tool_name
        self.tool_calls.append({
            "tool_name": tool_info["name"],
            "tool_type": tool_info["type"],
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info(f"🔵 WORKFLOW TOOL STARTED: {tool_name}")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool finishes executing. Only update tracked tools."""
        # Get the tool name from kwargs if available
        tool_name = kwargs.get("name")
        
        # Ignore if not a tracked tool
        if tool_name and tool_name not in self.tracked_tools:
            logger.debug(f"Ignoring internal tool end: {tool_name}")
            return
            
        if self.tool_calls and self.active_tool:
            # Find the matching active tool call (should be last one with status="started")
            for i in range(len(self.tool_calls) - 1, -1, -1):
                if self.tool_calls[i]["status"] == "started":
                    last_tool = self.tool_calls[i]
                    last_tool["status"] = "completed"
                    try:
                        # Handle different output types
                        if isinstance(output, str):
                            last_tool["result"] = json.loads(output) if output else {}
                        elif hasattr(output, "content"):
                            # Handle ToolMessage or similar objects
                            content = output.content
                            last_tool["result"] = json.loads(content) if isinstance(content, str) else content
                        else:
                            # Fallback: convert to string
                            last_tool["result"] = {"message": str(output)}
                        logger.info(f"✅ WORKFLOW TOOL COMPLETED: {self.active_tool}")
                        logger.debug(f"RESULT: {json.dumps(last_tool['result'], indent=2)}")
                    except (json.JSONDecodeError, AttributeError, TypeError) as e:
                        logger.warning(f"Failed to parse tool result: {e}")
                        last_tool["result"] = {"raw_output": str(output)}
                    self.active_tool = None
                    break
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when a tool encounters an error. Only track errors for tracked tools."""
        tool_name = kwargs.get("name")
        
        # Ignore if not a tracked tool
        if tool_name and tool_name not in self.tracked_tools:
            return
            
        if self.tool_calls and self.active_tool:
            # Find the last started tool
            for i in range(len(self.tool_calls) - 1, -1, -1):
                if self.tool_calls[i]["status"] == "started":
                    last_tool = self.tool_calls[i]
                    last_tool["status"] = "failed"
                    last_tool["error"] = str(error)
                    logger.error(f"❌ WORKFLOW TOOL FAILED: {self.active_tool} - {error}")
                    self.active_tool = None
                    break


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


class ToolCallInfo(BaseModel):
    """Information about a tool that was called during agent execution."""
    tool_name: str
    tool_type: Literal["scheduler", "assessment", "suggestions", "exam_generation", "progress_tracking", "context_update"]
    status: Literal["started", "completed", "failed"]
    result: Optional[Any] = None  # Changed from Dict to Any to support lists and other types
    error: Optional[str] = None
    timestamp: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client-defined session identifier")
    message: str = Field(..., description="User message for the agent")
    reset: bool = Field(False, description="Reset the chat session before sending the message")


class ChatResponse(BaseModel):
    session_id: str
    response: str
    history: List[ChatHistoryMessage]
    tool_calls: List[ToolCallInfo] = Field(default_factory=list, description="Tools that were called during this interaction")


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
        history: List[ChatHistoryMessage] = []
    else:
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

    # Create callback handler to track tool calls
    tracker = ToolCallTracker()
    runnable_config = {"callbacks": [tracker]}
    
    logger.info(f"CHAT REQUEST: session={payload.session_id}, message='{payload.message[:50]}...'")
    
    response_text = await agent.chat(payload.message, config=runnable_config)
    history = [
        ChatHistoryMessage(**entry) for entry in _serialize_chat_history(agent)
    ]
    
    # Convert tool calls to Pydantic models
    tool_call_info = [ToolCallInfo(**tc) for tc in tracker.tool_calls]
    
    logger.info(f"CHAT RESPONSE: {len(tool_call_info)} tool calls detected")
    for tc in tool_call_info:
        logger.info(f"  - {tc.tool_name} ({tc.tool_type}): {tc.status}")
    
    return ChatResponse(
        session_id=payload.session_id,
        response=response_text,
        history=history,
        tool_calls=tool_call_info,
    )


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


@app.get("/api/workflow/stream/{workflow_type}")
async def stream_workflow(workflow_type: str, session_id: str = "default"):
    """Stream workflow progress via Server-Sent Events (SSE).
    
    Args:
        workflow_type: Type of workflow (scheduler, suggestions, assessment, etc.)
        session_id: Session identifier for tracking
    
    Returns:
        StreamingResponse with SSE events
    """
    async def event_generator():
        """Generate SSE events for workflow progress."""
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'workflow_type': workflow_type})}\n\n"
        
        # Simulate workflow steps (in production, this would hook into LangGraph callbacks)
        if workflow_type == "scheduler":
            steps = [
                {"id": "check_auth", "name": "Checking Calendar Access", "status": "in_progress"},
                {"id": "check_auth", "name": "Checking Calendar Access", "status": "completed", "details": "Calendar authenticated"},
                {"id": "initialize", "name": "Parsing Meeting Requirements", "status": "in_progress"},
                {"id": "initialize", "name": "Parsing Meeting Requirements", "status": "completed"},
                {"id": "agent", "name": "Analyzing Schedule", "status": "in_progress"},
                {"id": "agent", "name": "Analyzing Schedule", "status": "completed", "details": "Found available slots"},
                {"id": "create_event", "name": "Creating Calendar Event", "status": "in_progress"},
                {"id": "create_event", "name": "Creating Calendar Event", "status": "completed"},
                {"id": "finalize", "name": "Finalizing", "status": "completed"},
            ]
            
            for step in steps:
                await asyncio.sleep(0.5)  # Simulate processing time
                event_data = {
                    "type": "step",
                    "timestamp": datetime.utcnow().isoformat(),
                    **step
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            # Send completion event with result
            result = {
                "type": "complete",
                "result": {
                    "event_id": f"evt-{int(datetime.utcnow().timestamp())}",
                    "meeting_name": "Study Session",
                    "start_time": datetime.utcnow().isoformat(),
                    "event_link": "https://calendar.google.com",
                }
            }
            yield f"data: {json.dumps(result)}\n\n"
        
        # Send done event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
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
# Exam generation endpoints
# --------------------------------------------------------------------------- #


@app.post("/api/generate-exam", response_model=ExamResponse)
async def generate_exam(
    files: List[UploadFile] = File(..., description="PDF files to process"),
    question_header: str = Form(..., description="Exam header/title"),
    question_description: str = Form(..., description="Question requirements"),
    api_key: Optional[str] = Form(None, description="OpenRouter API key"),
    model_name: Optional[str] = Form(None, description="AI model to use"),
):
    """Generate exam questions from uploaded PDF files."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    saved_paths: List[str] = []
    try:
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
            logger.info("Saved file: %s", file_path)

        final_api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not final_api_key:
            raise HTTPException(
                status_code=400,
                detail="API key required. Provide in form or set OPENROUTER_API_KEY env variable.",
            )

        api_base_url = os.getenv("EXAM_API_BASE_URL", "http://localhost:3000")
        default_model = os.getenv("EXAM_API_MODEL", "qwen/qwen3-30b-a3b:free")

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
            return ExamResponse(success=False, error=error)

        if not generated_questions:
            logger.warning("No questions were generated by the workflow.")
            return ExamResponse(
                success=False,
                error="No questions were generated. Please check your input.",
            )

        logger.info("Exam generation completed successfully.")
        return ExamResponse(
            success=True,
            questions=generated_questions,
            uploaded_files=[Path(path).name for path in saved_paths],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error during exam generation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        for path in saved_paths:
            try:
                Path(path).unlink()
            except FileNotFoundError:
                continue
            except Exception as exc:  # pragma: no cover - best effort cleanup
                logger.warning("Failed to delete temporary file %s: %s", path, exc)


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
