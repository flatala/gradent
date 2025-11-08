"""Planning workflow graph definition."""
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from .state import PlanningState
from .nodes import initialize_planning, planning_agent, create_plan, route_planning
from .tools import web_search


def create_planning_workflow() -> StateGraph:
    """Create the planning workflow graph.

    Flow:
    1. Initialize with system prompt
    2. Agent analyzes and may call tools (web_search, human_input)
    3. Tools execute if needed, loop back to agent
    4. When ready, create structured plan
    5. Return plan to caller

    Returns:
        Compiled planning workflow graph
    """
    workflow = StateGraph(PlanningState)

    workflow.add_node("initialize", initialize_planning)
    workflow.add_node("agent", planning_agent)
    workflow.add_node("tools", ToolNode([web_search]))
    workflow.add_node("create_plan", create_plan)

    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "agent")

    workflow.add_conditional_edges(
        "agent",
        route_planning,
        {
            "tools": "tools",
            "create_plan": "create_plan",
        },
    )

    workflow.add_edge("tools", "agent")
    workflow.add_edge("create_plan", END)

    return workflow.compile()

planning_graph = create_planning_workflow()
