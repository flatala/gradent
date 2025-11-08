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
from .tools import get_scheduler_tools, check_availability, schedule_meeting, cancel_meeting, get_upcoming_meetings

_logger = logging.getLogger("chat")


def create_scheduler_workflow() -> StateGraph:
    """Create the scheduler workflow graph.

    This workflow implements an autonomous scheduling agent that:
    1. Checks Google Calendar authentication
    2. Initializes with meeting requirements
    3. Agent analyzes requirements and makes scheduling decisions
    4. Agent can use 4 fixed operations: check_availability, schedule_meeting, cancel_meeting, get_upcoming_meetings
    5. When scheduling is complete or impossible, finalizes and returns result

    Flow:
    ```
    START
      ↓
    [check_auth] - Verify Google Calendar authentication
      ↓
    authenticated? ─NO→ [finalize] (return auth required message) → END
      ↓YES
    [initialize] - Parse meeting details and set up context
      ↓
    [agent] - Autonomous scheduling agent with 4 fixed operations
      ↓
    [conditional routing]
      ├→ [tools] - Execute calendar operations (check_availability, schedule_meeting, etc.)
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

    The agent can loop indefinitely, calling operations as needed, until it either:
    - Successfully creates an event (routes to "finalize")
    - Determines scheduling is impossible (routes to "failed" → "finalize")
    - Needs authentication (routes to "finalize" → END)

    Returns:
        Compiled scheduler workflow graph
    """
    workflow = StateGraph(SchedulerState)

    # Add nodes
    workflow.add_node("check_auth", check_calendar_auth)
    workflow.add_node("initialize", initialize_scheduler)
    workflow.add_node("agent", scheduling_agent)

    # ToolNode with fixed scheduler operations
    # No need for parameter injection - defaults are handled inside the operations
    from langchain_core.tools import StructuredTool

    tools = [
        StructuredTool.from_function(
            func=check_availability,
            name="check_availability",
            description="Check calendar availability for a specific time range. Returns existing events and indicates if the time slot is free.",
        ),
        StructuredTool.from_function(
            func=schedule_meeting,
            name="schedule_meeting",
            description="Create a new calendar event/meeting with title, time, attendees, and location. Use this after confirming time slot is available.",
        ),
        StructuredTool.from_function(
            func=cancel_meeting,
            name="cancel_meeting",
            description="Cancel/delete an existing calendar event by its event ID. Sends cancellation notifications to attendees.",
        ),
        StructuredTool.from_function(
            func=get_upcoming_meetings,
            name="get_upcoming_meetings",
            description="Retrieve upcoming meetings/events from the calendar for the next N days. Useful for viewing schedule.",
        ),
    ]

    tool_executor = ToolNode(tools)
    workflow.add_node("tools", tool_executor)

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
