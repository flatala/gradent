"""State definition for the assignment assessment workflow."""
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


class AssignmentInfo(BaseModel):
    """Input information about an assignment."""
    assignment_id: Optional[int] = Field(default=None, description="Database assignment ID if already exists")
    course_id: Optional[int] = Field(default=None, description="Database course ID if available")
    title: str = Field(description="Assignment title")
    description: Optional[str] = Field(default=None, description="Assignment description or requirements")
    course_name: Optional[str] = Field(default=None, description="Course name")
    due_date: Optional[datetime] = Field(default=None, description="Due date")
    raw_text: Optional[str] = Field(default=None, description="Raw assignment text from user")


class AssessmentResult(BaseModel):
    """Structured assessment output."""
    # Effort estimates (PERT-like)
    effort_hours_low: float = Field(description="Optimistic effort estimate (hours)")
    effort_hours_most: float = Field(description="Most likely effort estimate (hours)")
    effort_hours_high: float = Field(description="Pessimistic effort estimate (hours)")
    
    # Difficulty and risk
    difficulty_1to5: float = Field(description="Difficulty rating (1=very easy, 5=very hard)")
    weight_in_course: Optional[float] = Field(default=None, description="Estimated weight in course (0-100%)")
    risk_score_0to100: float = Field(description="Risk score considering complexity and time (0-100)")
    confidence_0to1: float = Field(description="AI confidence in this assessment (0-1)")
    
    # Structured breakdown
    milestones: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of milestones: {label, hours, days_before_due}"
    )
    prereq_topics: List[str] = Field(
        default_factory=list,
        description="Prerequisite topics or concepts needed"
    )
    deliverables: List[str] = Field(
        default_factory=list,
        description="What must be submitted"
    )
    blocking_dependencies: List[str] = Field(
        default_factory=list,
        description="External dependencies or blockers"
    )
    
    # Summary
    summary: str = Field(description="Brief summary of the assessment")


class AssessmentState(BaseModel):
    """State for the assignment assessment workflow."""
    
    # Input
    assignment_info: AssignmentInfo = Field(description="Assignment information to assess")
    user_id: Optional[int] = Field(default=None, description="User ID for context")
    
    # Message history for LLM
    messages: list = Field(default_factory=list, description="LLM conversation history")
    
    # Retrieved context (from vector DB in future)
    retrieved_context: Optional[str] = Field(default=None, description="Relevant course materials or rubrics")
    
    # Output
    assessment: Optional[AssessmentResult] = Field(default=None, description="Final structured assessment")
    
    # Database record ID (after saving)
    assessment_record_id: Optional[int] = Field(default=None, description="ID of saved assessment record")
    
    class Config:
        arbitrary_types_allowed = True
