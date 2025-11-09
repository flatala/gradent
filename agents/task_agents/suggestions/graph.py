"\"\"\"Suggestions workflow graph definition.\"\"\""
from langgraph.graph import StateGraph, START, END

from .nodes import generate_suggestions_node, summarize_context
from .state import SuggestionsState


def create_suggestions_workflow() -> StateGraph:
    """Create the suggestions workflow graph."""
    workflow = StateGraph(SuggestionsState)

    workflow.add_node("collect_context", summarize_context)
    workflow.add_node("generate_suggestions", generate_suggestions_node)

    workflow.add_edge(START, "collect_context")
    workflow.add_edge("collect_context", "generate_suggestions")
    workflow.add_edge("generate_suggestions", END)

    return workflow.compile()


suggestions_graph = create_suggestions_workflow()

