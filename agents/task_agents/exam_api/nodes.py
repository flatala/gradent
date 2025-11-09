"""Nodes for the exam API workflow."""
from typing import Dict, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from .state import ExamAPIState
from .tools import upload_pdfs_to_api, generate_questions_from_api


async def upload_pdfs(
    state: ExamAPIState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Upload PDF files to the question generation API.

    This node handles the POST request to upload files and stores
    the returned file identifiers.
    """
    result = await upload_pdfs_to_api.ainvoke(
        {
            "pdf_paths": state.pdf_paths,
            "question_header": state.question_header,
            "question_description": state.question_description,
            "api_key": state.api_key,
            "api_base_url": state.api_base_url,
            "model_name": state.model_name,
        },
        config=config
    )

    # Check for errors
    if "error" in result:
        return {
            "error": result["error"],
            "upload_status": "failed"
        }

    # Success
    return {
        "uploaded_files": result.get("uploaded_files", []),
        "upload_status": result.get("status", "success"),
        "messages": [
            HumanMessage(
                content=f"Uploaded {len(result.get('uploaded_files', []))} PDF(s) successfully"
            )
        ]
    }


async def generate_questions(
    state: ExamAPIState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Generate exam questions from uploaded PDFs.

    This node handles the GET request with SSE streaming and
    accumulates the generated content.
    """
    if not state.uploaded_files:
        return {"error": "No files uploaded yet"}

    result = await generate_questions_from_api.ainvoke(
        {
            "uploaded_files": state.uploaded_files,
            "question_header": state.question_header,
            "question_description": state.question_description,
            "api_key": state.api_key,
            "api_base_url": state.api_base_url,
            "model_name": state.model_name,
        },
        config=config
    )

    # Check if result is an error
    if result.startswith("Error"):
        return {
            "error": result,
            "messages": [HumanMessage(content=f"Generation failed: {result}")]
        }

    # Success
    return {
        "generated_questions": result,
        "messages": [
            HumanMessage(content="Successfully generated exam questions")
        ]
    }


def route_exam_api(
    state: ExamAPIState,
) -> Literal["upload", "generate", "end"]:
    """Route between workflow stages.

    Flow:
    1. If no uploaded files yet -> upload
    2. If uploaded but no questions -> generate
    3. If questions generated or error -> end
    """
    # Check for errors - end workflow
    if state.error:
        return "end"

    # Check if we have generated questions - end workflow
    if state.generated_questions:
        return "end"

    # If we have uploaded files but no questions yet - generate
    if state.uploaded_files and not state.generated_questions:
        return "generate"

    # Default: start with upload
    return "upload"
