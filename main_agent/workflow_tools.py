"""Tools that invoke workflow subgraphs."""
import json
import logging
from typing import Annotated
from time import perf_counter

from langchain_core.tools import tool, InjectedToolArg
from langchain_core.runnables import RunnableConfig
from workflows.planning import planning_graph, PlanningState
from workflows.assignment_assessment import assessment_graph, AssessmentState, AssignmentInfo
from shared.config import Configuration

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
    result = await planning_graph.ainvoke(initial_state, config)

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
    if _logger:
        try:
            _logger.info(
                "TOOL DONE: run_planning_workflow | status=no_plan | duration=%.2fs",
                perf_counter() - start,
            )
        except Exception:
            pass
    return "Planning workflow completed but no plan was generated."


@tool
async def assess_assignment(
    title: str,
    description: str,
    course_name: str = "Unknown Course",
    assignment_id: int = None,
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Assess the difficulty and effort required for an assignment.

    Use this tool when the user:
    - Shares an assignment and wants to understand how difficult it is
    - Asks how long an assignment will take
    - Wants help breaking down an assignment into milestones
    - Needs to plan study time for an assignment

    The workflow analyzes the assignment requirements and provides:
    - Effort estimates (low, most likely, high)
    - Difficulty rating
    - Risk score
    - Detailed milestones and timeline
    - Prerequisites and deliverables

    Args:
        title: The assignment title or name
        description: Full assignment description, requirements, or rubric
        course_name: Name of the course (optional)
        assignment_id: Database ID if the assignment already exists (optional)
        config: Injected configuration (automatically provided)

    Returns:
        Structured assessment with effort estimates, milestones, and breakdown (as JSON string)
    """
    cfg = Configuration.from_runnable_config(config)
    if _logger:
        try:
            _logger.info("TOOL CALL: assess_assignment | title=%s | course=%s", title, course_name)
        except Exception:
            pass

    start = perf_counter()

    # Create initial state
    assignment_info = AssignmentInfo(
        assignment_id=assignment_id,
        title=title,
        description=description,
        course_name=course_name,
    )
    
    initial_state = AssessmentState(assignment_info=assignment_info)
    
    try:
        result = await assessment_graph.ainvoke(initial_state, config)
        
        # Extract assessment
        if result.get("assessment"):
            assessment = result["assessment"]
            if _logger:
                try:
                    _logger.info(
                        "TOOL DONE: assess_assignment | status=ok | duration=%.2fs | effort_most=%.1f hrs | difficulty=%.1f/5",
                        perf_counter() - start,
                        assessment.effort_hours_most,
                        assessment.difficulty_1to5,
                    )
                except Exception:
                    pass
            
            # Return structured JSON
            return json.dumps({
                "title": title,
                "effort_estimates": {
                    "low_hours": assessment.effort_hours_low,
                    "most_likely_hours": assessment.effort_hours_most,
                    "high_hours": assessment.effort_hours_high,
                },
                "difficulty_1to5": assessment.difficulty_1to5,
                "risk_score_0to100": assessment.risk_score_0to100,
                "confidence": assessment.confidence_0to1,
                "milestones": assessment.milestones,
                "prerequisites": assessment.prereq_topics,
                "deliverables": assessment.deliverables,
                "blocking_dependencies": assessment.blocking_dependencies,
                "summary": assessment.summary,
                "saved_to_database": result.get("assessment_record_id") is not None,
            }, indent=2)
        
        # No assessment generated
        if _logger:
            try:
                _logger.info(
                    "TOOL DONE: assess_assignment | status=no_assessment | duration=%.2fs",
                    perf_counter() - start,
                )
            except Exception:
                pass
        return "Assessment workflow completed but no assessment was generated."
    
    except Exception as e:
        if _logger:
            try:
                _logger.error("TOOL ERROR: assess_assignment | error=%s", str(e))
            except Exception:
                pass
        return f"Error assessing assignment: {str(e)}"
