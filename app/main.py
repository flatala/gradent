"""FastAPI backend server for exam generation.

This server provides REST API endpoints for:
- Uploading PDF files
- Generating exam questions
- Health checks

The backend uses your existing LangGraph exam_api workflow.
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional
import logging

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import your workflow
from workflows.exam_api import exam_api_graph, ExamAPIState

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Exam Generation API",
    description="Generate exam questions from PDF files using AI",
    version="1.0.0"
)

# Configure CORS (allows frontend to call backend from different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory for uploaded files
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# Response models
class ExamResponse(BaseModel):
    """Response model for exam generation."""
    success: bool
    questions: Optional[str] = None
    error: Optional[str] = None
    uploaded_files: Optional[List[str]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str


# API Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return {
        "status": "ok",
        "message": "Exam Generation API is running"
    }


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Backend is operational"
    }


@app.post("/api/generate-exam", response_model=ExamResponse)
async def generate_exam(
    files: List[UploadFile] = File(..., description="PDF files to process"),
    question_header: str = Form(..., description="Exam header/title"),
    question_description: str = Form(..., description="Question requirements"),
    api_key: Optional[str] = Form(None, description="OpenRouter API key"),
    model_name: Optional[str] = Form(None, description="AI model to use"),
):
    """Generate exam questions from uploaded PDF files.
    
    Args:
        files: One or more PDF files
        question_header: Exam title (e.g., "Midterm Exam - CS 101")
        question_description: Requirements (e.g., "10 MCQ, 5 short answer")
        api_key: Optional API key (uses env var if not provided)
        model_name: Optional model name
        
    Returns:
        ExamResponse with generated questions or error
    """
    try:
        logger.info(f"Received request to generate exam with {len(files)} file(s)")
        logger.info(f"Header: {question_header}")
        logger.info(f"Description: {question_description}")
        
        # Validate files
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
        # Save uploaded files
        saved_paths = []
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is not a PDF"
                )
            
            # Save file to disk
            file_path = UPLOAD_DIR / file.filename
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            saved_paths.append(str(file_path.absolute()))
            logger.info(f"Saved file: {file_path}")
        
        # Get API key from form or environment
        final_api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not final_api_key:
            raise HTTPException(
                status_code=400,
                detail="API key required. Provide in form or set OPENROUTER_API_KEY env variable"
            )
        
        # Create workflow state
        state = ExamAPIState(
            pdf_paths=saved_paths,
            question_header=question_header,
            question_description=question_description,
            api_key=final_api_key,
            api_base_url="http://localhost:3000",  # Your Next.js API
            model_name=model_name or "qwen/qwen3-30b-a3b:free",
        )
        
        logger.info("Starting exam generation workflow...")
        
        # Run workflow
        result = await exam_api_graph.ainvoke(state)
        
        # Clean up uploaded files
        for path in saved_paths:
            try:
                Path(path).unlink()
                logger.info(f"Cleaned up: {path}")
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")
        
        # Handle both dict and object results from workflow
        if isinstance(result, dict):
            error = result.get("error")
            generated_questions = result.get("generated_questions")
        else:
            error = getattr(result, "error", None)
            generated_questions = getattr(result, "generated_questions", None)
        
        # Check for errors
        if error:
            logger.error(f"Workflow error: {error}")
            return ExamResponse(
                success=False,
                error=error
            )
        
        # Check if questions were generated
        if not generated_questions:
            logger.warning("No questions were generated")
            return ExamResponse(
                success=False,
                error="No questions were generated. Please check your input."
            )
        
        # Return success
        logger.info("Exam generation completed successfully")
        return ExamResponse(
            success=True,
            questions=generated_questions,
            uploaded_files=[Path(p).name for p in saved_paths]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cleanup")
async def cleanup_uploads():
    """Clean up all uploaded files (for testing)."""
    try:
        count = 0
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                file_path.unlink()
                count += 1
        
        return {
            "status": "ok",
            "message": f"Cleaned up {count} file(s)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    print("=" * 60)
    print("Starting Exam Generation Backend Server")
    print("=" * 60)
    print("Server will be available at: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
