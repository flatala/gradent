"""Workflow tool to invoke the exam API workflow from the main agent."""
import os
from typing import List

from langchain_core.tools import tool

from workflows.exam_api import exam_api_graph, ExamAPIState


@tool
async def run_exam_api_workflow(
    pdf_paths: List[str],
    question_header: str,
    question_description: str,
    api_key: str = None,
    api_base_url: str = "http://localhost:3000",
    model_name: str = None,
) -> str:
    """Generate exam questions from PDF files using an external API.

    This tool uploads PDFs to a question generation API and streams back
    generated exam questions in markdown format with MathJax support.

    Use this tool when the user wants to:
    - Create an exam from PDF materials
    - Generate practice questions from course documents
    - Build a test from lecture notes or textbooks

    Args:
        pdf_paths: List of paths to PDF files to process
        question_header: Exam title/header (e.g., "Midterm Exam - CS 101")
        question_description: Requirements for the exam (e.g., "10 MCQ, 5 short answer")
        api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
        api_base_url: API base URL (default: http://localhost:3000)
        model_name: AI model to use (optional)

    Returns:
        Generated exam questions as markdown, or error message

    Example:
        User: "Create a midterm exam from my lecture notes PDF"
        Assistant calls:
        run_exam_api_workflow(
            pdf_paths=["lecture_notes.pdf"],
            question_header="Midterm Exam - Biology 201",
            question_description="15 multiple choice (mixed difficulty), 5 short answer"
        )
    """
    # Use environment variable if api_key not provided
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: No API key provided. Set OPENROUTER_API_KEY environment variable or pass api_key parameter."

    # Create initial state
    state = ExamAPIState(
        pdf_paths=pdf_paths,
        question_header=question_header,
        question_description=question_description,
        api_key=api_key,
        api_base_url=api_base_url,
        model_name=model_name,
    )

    # Run the workflow
    result = await exam_api_graph.ainvoke(state)

    # Return result or error
    if result.error:
        return f"Error generating exam: {result.error}"

    if result.generated_questions:
        return result.generated_questions

    return "No questions were generated. Please check your input parameters and try again."
