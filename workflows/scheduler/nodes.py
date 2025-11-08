"""Nodes for the scheduler workflow."""
import os
import re
import base64
from urllib.parse import urlparse, parse_qs
import json
import logging
from typing import Dict, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from shared.config import Configuration
from shared.utils import get_orchestrator_llm
from shared.google_calendar import check_auth_status
from .state import ScheduledEvent, SchedulerState
from . import prompts

_logger = logging.getLogger("chat")


async def check_calendar_auth(
    state: SchedulerState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Check if user is authenticated with Google Calendar.

    If not authenticated, returns auth requirement message.
    """
    _logger.info("SCHEDULER: Checking calendar authentication...")
    auth_status = check_auth_status()
    _logger.info(f"SCHEDULER: Auth status = {auth_status}")

    if auth_status.get("authenticated"):
        # Already authenticated, proceed
        _logger.info("SCHEDULER: ✓ Authentication successful")
        return {"auth_required": False}

    # Need authentication
    _logger.warning(f"SCHEDULER: ✗ Authentication required: {auth_status.get('message')}")
    return {
        "auth_required": True,
        "auth_message": auth_status.get("message"),
    }


async def initialize_scheduler(
    state: SchedulerState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Initialize the scheduler workflow with system prompt and meeting details.

    This node sets up the initial context with:
    - System prompt defining the agent's role and capabilities
    - Meeting details parsed from the state
    - Initial analysis prompt to guide the agent
    """
    # Format attendee list for prompt
    attendees_str = ", ".join(state.attendee_emails) if state.attendee_emails else "None (solo event)"

    # Format constraints
    constraints_str = state.constraints if state.constraints else "None specified"

    # Format location
    location_str = state.location if state.location else "Not specified"

    # Create initial messages
    messages = [
        SystemMessage(content=prompts.SYSTEM_PROMPT),
        HumanMessage(
            content=prompts.INITIAL_ANALYSIS_PROMPT.format(
                meeting_name=state.meeting_name,
                topic=state.topic if state.topic else "Not specified",
                event_description=state.event_description,
                duration_minutes=state.duration_minutes,
                attendee_emails=attendees_str,
                location=location_str,
                constraints=constraints_str,
            )
        ),
    ]

    # Provide calendar configuration directly so the LLM includes it in tool calls
    default_cal_id = os.getenv("GOOGLE_CALENDAR_CALENDAR_ID") or os.getenv("GOOGLE_CALENDAR_DEFAULT_CALENDAR_ID")
    if default_cal_id:
        messages.append(
            SystemMessage(
                content=(
                    f"Calendar configuration: calendar_id={default_cal_id}. "
                    "Always include calendar_id in all calendar tool calls. "
                    "Do not use or mention 'primary'. Do not ask to confirm calendar."
                )
            )
        )

    default_tz = os.getenv("GOOGLE_CALENDAR_TIME_ZONE") or os.getenv("TIME_ZONE")
    if default_tz:
        messages.append(
            SystemMessage(
                content=(
                    f"Calendar timezone: {default_tz}. Interpret relative dates like 'tomorrow' in this timezone and "
                    "include time_zone when creating events."
                )
            )
        )

    return {"messages": messages}


async def scheduling_agent(
    state: SchedulerState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Core agent node that autonomously schedules events using Google Calendar tools.

    This node:
    - Uses the orchestrator LLM for reasoning
    - Has access to LangChain's CalendarToolkit tools
    - Can loop multiple times, calling tools as needed
    - Decides when scheduling is complete or impossible
    """
    from .tools import load_calendar_tools

    _logger.info("SCHEDULER: Agent node - loading tools...")
    cfg = Configuration.from_runnable_config(config)
    llm = get_orchestrator_llm(cfg)

    # Load Google Calendar tools from LangChain toolkit
    try:
        tools = load_calendar_tools()
        _logger.info(f"SCHEDULER: Loaded {len(tools)} calendar tools: {[t.name for t in tools]}")
    except Exception as e:
        _logger.error(f"SCHEDULER: Failed to load calendar tools: {e}")
        raise

    llm_with_tools = llm.bind_tools(tools)

    # Invoke the LLM with current message history
    _logger.info(f"SCHEDULER: Agent invoking LLM with {len(state.messages)} messages...")
    response = await llm_with_tools.ainvoke(state.messages)

    # Log what the agent decided to do
    if hasattr(response, 'tool_calls') and response.tool_calls:
        _logger.info(f"SCHEDULER: Agent decided to call {len(response.tool_calls)} tool(s): {[tc.get('name') for tc in response.tool_calls]}")
    else:
        _logger.info("SCHEDULER: Agent did not call any tools")

    return {"messages": [response]}


async def finalize_scheduling(
    state: SchedulerState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Finalize the scheduling process and extract event details.

    This node:
    - Analyzes the message history to determine success or failure
    - Extracts event details from create_calendar_event tool responses
    - Formats the final ScheduledEvent or error reasoning
    """
    from shared.utils import get_text_llm

    _logger.info("SCHEDULER: Finalizing scheduling process...")
    _logger.info(f"SCHEDULER: Total messages in history: {len(state.messages)}")

    # Log all messages for debugging
    for i, msg in enumerate(state.messages):
        msg_type = type(msg).__name__
        has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
        content_preview = str(msg.content)[:200] if hasattr(msg, 'content') else 'N/A'
        _logger.debug(f"SCHEDULER: Message {i}: {msg_type}, has_tool_calls={has_tool_calls}, content={content_preview}...")

    cfg = Configuration.from_runnable_config(config)
    llm = get_text_llm(cfg)

    # Helpers
    def _strip_code_fences(s: str) -> str:
        if '```json' in s:
            try:
                return s.split('```json', 1)[1].split('```', 1)[0].strip()
            except Exception:
                return s
        if '```' in s:
            try:
                return s.split('```', 1)[1].split('```', 1)[0].strip()
            except Exception:
                return s
        return s

    def _extract_event_id_from_link(link: str) -> str | None:
        try:
            parsed = urlparse(link)
            qs = parse_qs(parsed.query)
            eid_vals = qs.get("eid")
            if not eid_vals:
                return None
            eid = eid_vals[0]
            # Try to decode Google Calendar eid (urlsafe base64 of "<eventId> <calendarId>")
            try:
                # Pad to multiple of 4
                padded = eid + ("=" * (-len(eid) % 4))
                decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")
                # Expect "eventId calendarId"; take first token
                parts = decoded.split()
                if parts:
                    return parts[0]
            except Exception:
                # Fall back to returning the raw eid if decoding fails
                return eid
            return eid
        except Exception:
            return None

    def _parse_tool_content(content: str) -> dict:
        # Try strict JSON
        s = _strip_code_fences(content)
        try:
            data = json.loads(s)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        # Try to extract minimal fields via regex heuristics
        result = {}
        m = re.search(r"\b(id|event_id)\b\W*[:=]\W*([A-Za-z0-9_\-]+)", content)
        if m:
            result['event_id'] = m.group(2)
        m = re.search(r"https?://\S+calendar\S+", content)
        if m:
            link = m.group(0)
            result['calendar_link'] = link
            # Try to derive event_id from eid param in the link
            ev_id = _extract_event_id_from_link(link)
            if ev_id and 'event_id' not in result:
                result['event_id'] = ev_id
        m = re.search(r"hangoutLink\W*[:=]\W*(https?://\S+)", content)
        if m:
            result['meeting_link'] = m.group(1)
        # Not reliable, but return whatever was found
        return result

    # Track last create_calendar_event call args to fill gaps
    create_args = None
    event_data = None
    event_created = False

    for msg in reversed(state.messages):
        # Capture tool call args
        if isinstance(msg, AIMessage) and getattr(msg, 'tool_calls', None):
            for tc in msg.tool_calls:
                if 'create_calendar_event' in (tc.get('name') or ''):
                    create_args = tc.get('args') or create_args
        # Capture tool response
        if isinstance(msg, ToolMessage) and msg.name == 'create_calendar_event':
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            parsed = _parse_tool_content(content)
            # Consider it created if we got any dict back (even minimal)
            if parsed:
                event_data = parsed
                event_created = True
                break

    if event_created:
        # Successfully created event - extract details
        try:
            # Prefer parsed tool data; fall back to tool call args
            ed = event_data or {}
            args = create_args or {}
            # Normalize fields
            event_id = ed.get('event_id') or ed.get('id') or 'unknown'
            title = ed.get('title') or ed.get('summary') or args.get('summary') or state.meeting_name
            # Start/end may be dicts or strings
            def _normalize_time(x):
                if isinstance(x, dict):
                    return x.get('dateTime') or x.get('date') or json.dumps(x)
                return x
            start_time = _normalize_time(ed.get('start')) or _normalize_time(args.get('start')) or 'unknown'
            end_time = _normalize_time(ed.get('end')) or _normalize_time(args.get('end')) or 'unknown'
            # Attendees may be list[dict] or list[str]
            attendees = ed.get('attendees') or args.get('attendees') or state.attendee_emails
            if isinstance(attendees, list):
                attendees_emails = []
                for a in attendees:
                    if isinstance(a, str):
                        attendees_emails.append(a)
                    elif isinstance(a, dict) and a.get('email'):
                        attendees_emails.append(a['email'])
                attendees = attendees_emails
            location = ed.get('location') or args.get('location') or state.location
            meeting_link = ed.get('meeting_link') or ed.get('hangoutLink')
            calendar_link = ed.get('calendar_link') or ed.get('htmlLink')

            scheduled_event = ScheduledEvent(
                event_id=event_id,
                title=title,
                description=ed.get('description') or state.event_description,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=state.duration_minutes,
                attendees=attendees or [],
                location=location,
                meeting_link=meeting_link,
                calendar_link=calendar_link,
            )

            reasoning = f"Successfully scheduled '{state.meeting_name}' for {scheduled_event.start_time}"
            if state.attendee_emails:
                reasoning += f" with {len(state.attendee_emails)} attendee(s)"

            return {
                "scheduled_event": scheduled_event,
                "reasoning": reasoning,
            }
        except Exception as e:
            # Fallback with partial data
            return {
                "scheduled_event": None,
                "reasoning": f"Event may have been created but details extraction failed: {str(e)}",
            }
    else:
        # Failed to create event - analyze why
        # Use LLM to generate helpful failure message
        failure_prompt = HumanMessage(content=prompts.FINALIZE_FAILURE_PROMPT)
        messages = state.messages + [failure_prompt]

        response = await llm.ainvoke(messages)

        return {
            "scheduled_event": None,
            "reasoning": response.content,
        }


def route_scheduler(
    state: SchedulerState,
) -> Literal["tools", "finalize", "failed", "need_auth"]:
    """Route between tool execution, finalization, failure, and auth states.

    Routing logic:
    - If auth required -> route to "need_auth"
    - If last message has tool calls -> route to "tools" to execute them
    - If create_calendar_event was successfully called -> route to "finalize"
    - If agent gave up or determined scheduling is impossible -> route to "failed"
    - Otherwise -> route to "finalize" (agent finished without tool calls)
    """
    # Check if auth is required
    if state.auth_required:
        return "need_auth"

    messages = state.messages
    if not messages:
        return "finalize"

    last_message = messages[-1]

    # Check if last message is an AIMessage with tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    # Check if create_calendar_event was called in recent messages
    for msg in reversed(messages[-5:]):  # Check last 5 messages
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if 'create_calendar_event' in tool_call.get('name', ''):
                    # Event was created, finalize
                    return "finalize"

    # Check if agent explicitly indicated failure or inability to schedule
    if isinstance(last_message, AIMessage) and last_message.content:
        content_lower = last_message.content.lower()
        failure_indicators = [
            'unable to schedule',
            'cannot schedule',
            'no available slots',
            'failed to',
            'impossible to',
        ]
        if any(indicator in content_lower for indicator in failure_indicators):
            return "failed"

    # Default to finalize if no tool calls and no failure indicators
    return "finalize"
