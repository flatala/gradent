"""Nodes for the planning workflow."""
import json
from typing import Dict, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from shared.config import Configuration
from shared.utils import get_orchestrator_llm
from .state import Plan, PlanningState
from . import prompts


async def initialize_planning(
    state: PlanningState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Initialize the planning workflow with system prompt and user query."""
    messages = [
        SystemMessage(content=prompts.SYSTEM_PROMPT),
        HumanMessage(content=prompts.INITIAL_ANALYSIS_PROMPT.format(query=state.query)),
    ]

    return {"messages": messages}


async def planning_agent(
    state: PlanningState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Agent node that analyzes requests and can call tools.

    This node:
    - Uses the orchestrator LLM for reasoning
    - Can call web_search tool
    - Decides when enough information is gathered
    """
    from .tools import web_search

    cfg = Configuration.from_runnable_config(config)
    llm = get_orchestrator_llm(cfg)

    # Bind tools to the LLM (no human_input to avoid interrupts)
    llm_with_tools = llm.bind_tools([web_search])

    # Invoke the LLM
    response = await llm_with_tools.ainvoke(state.messages)

    return {"messages": [response]}


async def create_plan(
    state: PlanningState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Create the final structured plan.

    This node:
    - Uses the text LLM to generate the plan
    - Formats output as structured JSON
    - Parses and validates the plan
    """
    from shared.utils import get_text_llm

    cfg = Configuration.from_runnable_config(config)
    llm = get_text_llm(cfg)

    # Add planning prompt to messages
    messages = state.messages + [
        HumanMessage(content=prompts.PLANNING_PROMPT.format(query=state.query))
    ]

    # Get response
    response = await llm.ainvoke(messages)

    # Parse the plan from JSON
    try:
        # Extract JSON from response (handle markdown code blocks)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        plan_data = json.loads(content)
        plan = Plan(**plan_data)

        return {
            "plan": plan,
            "messages": [response],
        }

    except Exception as e:
        # Fallback: create a simple plan from the response
        return {
            "plan": Plan(
                goal=state.query,
                steps=[response.content],
                considerations=["Plan parsing failed - using raw response"]
            ),
            "messages": [response],
        }


def route_planning(
    state: PlanningState,
) -> Literal["tools", "create_plan"]:
    """Route between tool execution and plan creation.

    If the last message has tool calls, route to tools.
    Otherwise, move to plan creation.
    """
    messages = state.messages
    if not messages:
        return "create_plan"

    last_message = messages[-1]

    # Check if last message is an AIMessage with tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "create_plan"
