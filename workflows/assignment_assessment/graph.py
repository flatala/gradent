"""Assignment assessment workflow graph definition."""
from langgraph.graph import StateGraph, START, END

from .state import AssessmentState
from .nodes import (
    initialize_assessment,
    analyze_assignment,
    generate_structured_assessment,
    save_to_database,
)


def create_assessment_workflow() -> StateGraph:
    """Create the assignment assessment workflow graph.
    
    Flow:
    1. Initialize with system prompt and assignment details
    2. Analyze assignment (reasoning step)
    3. Generate structured assessment (JSON output)
    4. Save to database
    5. Return assessment to caller
    
    Returns:
        Compiled assessment workflow graph
    """
    workflow = StateGraph(AssessmentState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_assessment)
    workflow.add_node("analyze", analyze_assignment)
    workflow.add_node("generate_assessment", generate_structured_assessment)
    workflow.add_node("save_to_db", save_to_database)
    
    # Define linear flow
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "analyze")
    workflow.add_edge("analyze", "generate_assessment")
    workflow.add_edge("generate_assessment", "save_to_db")
    workflow.add_edge("save_to_db", END)
    
    return workflow.compile()


# Export the compiled graph
assessment_graph = create_assessment_workflow()
