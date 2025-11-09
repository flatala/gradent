"""Exam API workflow graph definition."""
from langgraph.graph import StateGraph, START, END

from .state import ExamAPIState
from .nodes import upload_pdfs, generate_questions, route_exam_api


def create_exam_api_workflow() -> StateGraph:
    """Create the exam API workflow graph.

    Flow:
    1. Upload PDFs to the API (POST /api/generate-questions)
    2. Generate questions via streaming (GET /api/generate-questions)
    3. Return generated questions as markdown

    Returns:
        Compiled exam API workflow graph
    """
    workflow = StateGraph(ExamAPIState)

    # Add nodes
    workflow.add_node("upload", upload_pdfs)
    workflow.add_node("generate", generate_questions)

    # Define flow with routing
    workflow.add_conditional_edges(
        START,
        route_exam_api,
        {
            "upload": "upload",
            "generate": "generate",
            "end": END,
        },
    )

    # After upload, route to generation or end
    workflow.add_conditional_edges(
        "upload",
        route_exam_api,
        {
            "generate": "generate",
            "end": END,
        },
    )

    # After generation, end
    workflow.add_edge("generate", END)

    return workflow.compile()


# Export the compiled graph
exam_api_graph = create_exam_api_workflow()
