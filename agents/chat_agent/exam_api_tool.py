"""Workflow tool to invoke the exam API workflow from the main agent."""
import os
from typing import List
from dotenv import load_dotenv

from langchain_core.tools import tool

from workflows.exam_api import exam_api_graph, ExamAPIState

# Load environment variables from .env file
load_dotenv()


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

    # Append instruction to avoid including answers inline
    enhanced_description = f"{question_description} IMPORTANT: Do NOT include the correct answers at any point - neither next to the questions nor in a separate section at the end. Do not include 'marks'."

    # Create initial state
    state = ExamAPIState(
        pdf_paths=pdf_paths,
        question_header=question_header,
        question_description=enhanced_description,
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
        print('JAJECZKO')
        # Remove everything after "**Section B: Answers**"
        output = result.generated_questions.split("**Section B: Answers**")[0].strip()
        return output

    return "No questions were generated. Please check your input parameters and try again."
