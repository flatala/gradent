"""State definition for the planning workflow."""
from typing import List, Optional, Annotated

from pydantic import BaseModel, Field
from langgraph.graph import add_messages


class Plan(BaseModel):
    """A structured plan with steps."""
    goal: str = Field(description="The main goal or objective")
    steps: List[str] = Field(description="List of steps to achieve the goal")
    considerations: List[str] = Field(default_factory=list, description="Important considerations or constraints")


class PlanningState(BaseModel):
    """State for the planning workflow.

    This state tracks the planning process including:
    - The original query/request
    - Message history for LLM interactions
    - Search results from web research
    - The final structured plan
    """

    # Input
    query: str = Field(description="The planning query or request")

    # Message history (append-only merge using LangGraph's add_messages reducer)
    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="LLM conversation history"
    )

    # Intermediate data
    search_results: Optional[List[dict]] = Field(
        default=None,
        description="Results from web search (if applicable)"
    )

    # Output
    plan: Optional[Plan] = Field(default=None, description="The final structured plan")

    class Config:
        arbitrary_types_allowed = True
