"""Nodes for the scheduler workflow."""
import os
import re
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

    cfg = Configuration.from_runnable_config(config)
    llm = get_text_llm(cfg)

    # Helper to strip code fences from JSON
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

    # Helper to parse tool content
    def _parse_tool_content(content: str) -> dict:
        s = _strip_code_fences(content)
        try:
            data = json.loads(s)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        
        # If JSON parsing fails, try to extract the event link from plain text
        result = {}
        if "Event created:" in content:
            import re
            link_match = re.search(r'https://www\.google\.com/calendar/event\?eid=[^\s]+', content)
            if link_match:
                result['htmlLink'] = link_match.group(0)
        return result

    # Helper to normalize time fields
    def _normalize_time(x):
        if isinstance(x, dict):
            return x.get('dateTime') or x.get('date') or json.dumps(x)
        return x

    # Look for create_calendar_event tool call and response
    create_args = None
    event_data = None
    event_created = False

    for msg in reversed(state.messages):
        # Capture tool call args
        if isinstance(msg, AIMessage) and getattr(msg, 'tool_calls', None):
            for tc in msg.tool_calls:
                if tc.get('name') == 'create_calendar_event':
                    create_args = tc.get('args') or create_args
        # Capture tool response
        if isinstance(msg, ToolMessage) and msg.name == 'create_calendar_event':
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            parsed = _parse_tool_content(content)
            if parsed:
                event_data = parsed
                event_created = True
                break

    if event_created:
        # Successfully created event - extract details
        try:
            ed = event_data or {}
            args = create_args or {}

            # Extract fields (CalendarToolkit returns id, summary, start, end, attendees, location, htmlLink, hangoutLink)
            event_id = ed.get('id') or 'unknown'
            title = ed.get('summary') or args.get('summary') or state.meeting_name
            start_time = _normalize_time(ed.get('start')) or _normalize_time(args.get('start')) or 'unknown'
            end_time = _normalize_time(ed.get('end')) or _normalize_time(args.get('end')) or 'unknown'
            
            # Attendees may be list[dict] with 'email' key
            attendees = ed.get('attendees') or args.get('attendees') or state.attendee_emails
            if isinstance(attendees, list):
                attendees_emails = []
                for a in attendees:
                    if isinstance(a, str):
                        attendees_emails.append(a)
                    elif isinstance(a, dict) and a.get('email'):
                        attendees_emails.append(a['email'])
                attendees = attendees_emails

            scheduled_event = ScheduledEvent(
                event_id=event_id,
                title=title,
                description=ed.get('description') or state.event_description,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=state.duration_minutes,
                attendees=attendees or [],
                location=ed.get('location') or args.get('location') or state.location,
                meeting_link=ed.get('hangoutLink'),
                calendar_link=ed.get('htmlLink'),
            )

            reasoning = f"Successfully scheduled '{state.meeting_name}' for {scheduled_event.start_time}"
            if state.attendee_emails:
                reasoning += f" with {len(state.attendee_emails)} attendee(s)"

            return {
                "scheduled_event": scheduled_event,
                "reasoning": reasoning,
            }
        except Exception as e:
            _logger.error(f"SCHEDULER: Failed to extract event details: {e}", exc_info=True)
            return {
                "scheduled_event": None,
                "reasoning": f"Event may have been created but details extraction failed: {str(e)}",
            }
    else:
        # Failed to create event - analyze why
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
