"""Scheduler workflow graph definition."""
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from .state import SchedulerState
from .nodes import (
    check_calendar_auth,
    initialize_scheduler,
    scheduling_agent,
    finalize_scheduling,
    route_scheduler,
)
from .tools import load_calendar_tools

_logger = logging.getLogger("chat")


def create_scheduler_workflow() -> StateGraph:
    """Create the scheduler workflow graph.

    This workflow implements an autonomous scheduling agent that:
    1. Checks Google Calendar authentication
    2. Initializes with meeting requirements
    3. Agent analyzes requirements and makes scheduling decisions
    4. Agent can loop through tools (find_free_time_slots, create_calendar_event, etc.)
    5. When scheduling is complete or impossible, finalizes and returns result

    Flow:
    ```
    START
      ↓
    [check_auth] - Verify Google Calendar OAuth
      ↓
    authenticated? ─NO→ [END] (return auth required message)
      ↓YES
    [initialize] - Parse meeting details and set up context
      ↓
    [agent] - Autonomous scheduling agent with Google Calendar tools
      ↓
    [conditional routing]
      ├→ [tools] - Execute Google Calendar API calls
      │    ↓
      │  [agent] - Loop back for next decision
      │
      ├→ [finalize] - Extract and return scheduled event details
      │    ↓
      │   END
      │
      └→ [failed] - Handle scheduling failure
           ↓
          END (via finalize node)
    ```

    The agent can loop indefinitely, calling tools as needed, until it either:
    - Successfully creates an event (routes to "finalize")
    - Determines scheduling is impossible (routes to "failed" → "finalize")
    - Needs authentication (routes to "need_auth" → END)

    Returns:
        Compiled scheduler workflow graph
    """
    workflow = StateGraph(SchedulerState)

    # Add nodes
    workflow.add_node("check_auth", check_calendar_auth)
    workflow.add_node("initialize", initialize_scheduler)
    workflow.add_node("agent", scheduling_agent)

    # ToolNode with LangChain CalendarToolkit tools
    # Tools are loaded dynamically to ensure auth is ready
    async def tools_node(state: SchedulerState):
        """Dynamic tool node that loads Calendar tools."""
        _logger.info("SCHEDULER GRAPH: Entering tools node...")
        tools = load_calendar_tools()
        # Inject default calendar_id into pending tool calls if missing
        try:
            import os
            from langchain_core.messages import AIMessage
            default_cal_id = os.getenv("GOOGLE_CALENDAR_CALENDAR_ID") or os.getenv("GOOGLE_CALENDAR_DEFAULT_CALENDAR_ID")
            default_tz = os.getenv("GOOGLE_CALENDAR_TIME_ZONE") or os.getenv("TIME_ZONE")
            if default_cal_id and state.messages:
                last = state.messages[-1]
                if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
                    for tc in last.tool_calls:
                        name = tc.get("name") or ""
                        args = tc.get("args") or {}
                        if name in {"create_calendar_event", "search_events", "update_calendar_event", "delete_calendar_event", "move_calendar_event"}:
                            if "calendar_id" not in args:
                                args["calendar_id"] = default_cal_id
                                tc["args"] = args
                            if name == "create_calendar_event" and default_tz and "time_zone" not in args:
                                args["time_zone"] = default_tz
                                tc["args"] = args
                    _logger.info("SCHEDULER GRAPH: Injected default calendar_id into tool call args")
        except Exception as e:
            _logger.debug(f"SCHEDULER GRAPH: calendar_id injection skipped: {e}")
        tool_executor = ToolNode(tools)
        _logger.info("SCHEDULER GRAPH: Executing tools...")
        result = await tool_executor.ainvoke(state)
        _logger.info("SCHEDULER GRAPH: Tools executed successfully")
        return result

    workflow.add_node("tools", tools_node)

    workflow.add_node("finalize", finalize_scheduling)

    # Define edges
    workflow.add_edge(START, "check_auth")

    # After auth check, route based on auth status
    def route_auth(state: SchedulerState):
        if state.auth_required:
            _logger.info("SCHEDULER GRAPH: Routing to finalize (auth required)")
            return "finalize"  # Return auth message to user
        _logger.info("SCHEDULER GRAPH: Routing to initialize (authenticated)")
        return "initialize"

    workflow.add_conditional_edges(
        "check_auth",
        route_auth,
        {
            "initialize": "initialize",
            "finalize": "finalize",
        }
    )

    workflow.add_edge("initialize", "agent")

    # Conditional routing from agent
    workflow.add_conditional_edges(
        "agent",
        route_scheduler,
        {
            "tools": "tools",        # Execute Google Calendar tools
            "finalize": "finalize",  # Success - extract event details
            "failed": "finalize",    # Failure - explain why
            "need_auth": "finalize", # Auth needed mid-workflow
        },
    )

    # Loop back to agent after tool execution
    workflow.add_edge("tools", "agent")

    # Finalize ends the workflow
    workflow.add_edge("finalize", END)

    return workflow.compile()


# Create and export the compiled graph
scheduler_graph = create_scheduler_workflow()
