"""Tools for the exam API workflow."""
import httpx
from typing import Annotated, List, Dict, Optional
from pathlib import Path

from langchain_core.tools import tool, InjectedToolArg
from langchain_core.runnables import RunnableConfig

from shared.config import Configuration


@tool
async def upload_pdfs_to_api(
    pdf_paths: List[str],
    question_header: str,
    question_description: str,
    api_key: str,
    api_base_url: str = "http://localhost:3000",
    model_name: Optional[str] = None,
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> Dict:
    """Upload PDF files to the question generation API.

    Args:
        pdf_paths: List of paths to PDF files to upload
        question_header: Exam header details
        question_description: Question paper requirements
        api_key: OpenRouter API key
        api_base_url: Base URL of the API (default: http://localhost:3000)
        model_name: Optional AI model name
        config: Injected configuration (automatically provided)

    Returns:
        Dictionary with uploaded file names and status
    """
    try:
        files = []
        for idx, pdf_path in enumerate(pdf_paths):
            path = Path(pdf_path)
            if not path.exists():
                return {"error": f"PDF file not found: {pdf_path}"}
            
            # Open file for upload
            files.append(
                (f"file-{idx}", (path.name, open(path, "rb"), "application/pdf"))
            )

        # Prepare form data
        data = {
            "questionHeader": question_header,
            "questionDescription": question_description,
            "apiKey": api_key,
        }
        
        if model_name:
            data["modelName"] = model_name

        # Make POST request
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{api_base_url}/api/generate-questions",
                files=files,
                data=data
            )
            
            # Close file handles
            for _, (_, file_handle, _) in files:
                file_handle.close()

            if response.status_code != 200:
                return {
                    "error": f"Upload failed with status {response.status_code}",
                    "detail": response.text
                }

            result = response.json()
            return {
                "status": "success",
                "uploaded_files": result.get("uploadedFiles", []),
                "message": result.get("message", "")
            }

    except Exception as e:
        return {"error": f"Upload failed: {str(e)}"}


@tool
async def generate_questions_from_api(
    uploaded_files: List[str],
    question_header: str,
    question_description: str,
    api_key: str,
    api_base_url: str = "http://localhost:3000",
    model_name: Optional[str] = None,
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Generate exam questions from uploaded PDFs using the API.

    This tool handles Server-Sent Events (SSE) streaming from the API.

    Args:
        uploaded_files: List of uploaded file names (from upload response)
        question_header: Exam header details
        question_description: Question paper requirements
        api_key: OpenRouter API key
        api_base_url: Base URL of the API (default: http://localhost:3000)
        model_name: Optional AI model name
        config: Injected configuration (automatically provided)

    Returns:
        Generated exam questions as markdown string
    """
    try:
        # Prepare query parameters
        params = {
            "questionHeader": question_header,
            "questionDescription": question_description,
            "apiKey": api_key,
            "uploadedFiles": ",".join(uploaded_files)
        }
        
        if model_name:
            params["modelName"] = model_name

        generated_content = []

        # Make streaming GET request
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "GET",
                f"{api_base_url}/api/generate-questions",
                params=params
            ) as response:
                if response.status_code != 200:
                    return f"Error: Generation failed with status {response.status_code}"

                # Process Server-Sent Events
                current_event = None
                async for line in response.aiter_lines():
                    # Handle event type lines
                    if line.startswith("event: "):
                        current_event = line[7:].strip()
                        # Check for completion event
                        if current_event == "complete":
                            print("Stream complete event received")
                            break
                        continue
                    
                    # Handle data lines
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        
                        # Check for completion signals
                        if data in ["[DONE]", "done"]:
                            print("Stream done signal received")
                            break
                        
                        # Try to parse JSON data
                        try:
                            import json
                            parsed = json.loads(data)
                            
                            # Check for error type
                            if parsed.get("type") == "error":
                                return f"Error: {parsed.get('content', 'Unknown error')}"
                            
                            # Extract markdown content
                            if parsed.get("type") == "markdown":
                                content = parsed.get("content", "")
                                if content:
                                    print(f"Received markdown chunk: {len(content)} chars")
                                    generated_content.append(content)
                        except json.JSONDecodeError:
                            # Not JSON, treat as plain text
                            # Only treat it as an error if it explicitly starts with "Error:" or "error:"
                            if data.strip().lower().startswith("error:"):
                                return f"Error during generation: {data}"
                            # Otherwise, treat as markdown content
                            if data.strip():
                                generated_content.append(data)

        if not generated_content:
            return "Error: No content generated"

        return "".join(generated_content)

    except Exception as e:
        return f"Error generating questions: {str(e)}"
