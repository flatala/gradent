"""State definition for the exam API workflow."""
from typing import List, Optional, Annotated

from pydantic import BaseModel, Field
from langgraph.graph import add_messages


class ExamAPIState(BaseModel):
    """State for the exam API workflow.

    This state tracks the process of uploading PDFs and generating
    exam questions via an external API.
    """

    # Input parameters
    pdf_paths: List[str] = Field(
        description="Paths to PDF files to process"
    )
    question_header: str = Field(
        description="Exam header details (e.g., 'Midterm Exam - Physics 101')"
    )
    question_description: str = Field(
        description="Question paper requirements (e.g., '10 multiple choice, 5 short answer')"
    )
    api_key: str = Field(
        description="OpenRouter API key for generation"
    )
    api_base_url: str = Field(
        default="http://localhost:3000",
        description="Base URL of the question generation API"
    )
    model_name: Optional[str] = Field(
        default=None,
        description="AI model name to use (optional)"
    )

    # Message history (for agent interactions)
    messages: Annotated[list, add_messages] = Field(
        default_factory=list,
        description="LLM conversation history"
    )

    # Intermediate data
    uploaded_files: Optional[List[str]] = Field(
        default=None,
        description="List of uploaded file identifiers from API"
    )
    upload_status: Optional[str] = Field(
        default=None,
        description="Status of the upload operation"
    )

    # Output
    generated_questions: Optional[str] = Field(
        default=None,
        description="Generated exam questions (markdown format)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if something went wrong"
    )

    class Config:
        arbitrary_types_allowed = True
