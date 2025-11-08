"""Tools that invoke workflow subgraphs."""
import json
import logging
import os
import time
from typing import Annotated
from time import perf_counter

from langchain_core.tools import tool, InjectedToolArg
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage

from workflows.planning import planning_graph, PlanningState
from workflows.planning import prompts
from shared.config import Configuration
from shared.utils import get_text_llm

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
    # No fallback path: surface a clear error
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
