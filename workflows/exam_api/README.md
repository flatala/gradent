# Exam API Workflow

LangGraph workflow that integrates with an external question generation API to create exam questions from PDF documents.

## Overview

This workflow provides a simple interface to:
1. Upload PDF files to a question generation API
2. Stream generated exam questions in real-time
3. Return formatted markdown output

## Architecture

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       v
┌─────────────┐
│   Upload    │  ← POST /api/generate-questions
│    PDFs     │    (multipart/form-data)
└──────┬──────┘
       │
       v
┌─────────────┐
│  Generate   │  ← GET /api/generate-questions
│  Questions  │    (Server-Sent Events streaming)
└──────┬──────┘
       │
       v
┌─────────────┐
│     END     │
└─────────────┘
```

## Files

- **`state.py`**: `ExamAPIState` - workflow state definition
- **`tools.py`**: HTTP client tools for API interaction
  - `upload_pdfs_to_api` - Uploads PDFs via POST
  - `generate_questions_from_api` - Streams questions via GET with SSE
- **`nodes.py`**: Workflow nodes
  - `upload_pdfs` - Handles file upload
  - `generate_questions` - Handles streaming generation
  - `route_exam_api` - Routes between stages
- **`graph.py`**: LangGraph workflow definition

## Usage

### Basic Example

```python
import asyncio
from workflows.exam_api import exam_api_graph, ExamAPIState

async def generate_exam():
    state = ExamAPIState(
        pdf_paths=["lecture_notes.pdf", "textbook.pdf"],
        question_header="Midterm Exam - Physics 101",
        question_description="10 MCQ (easy-medium), 5 short answer (hard)",
        api_key="your-openrouter-api-key",
        api_base_url="http://localhost:3000",
    )
    
    result = await exam_api_graph.ainvoke(state)
    
    if result.generated_questions:
        print(result.generated_questions)
    elif result.error:
        print(f"Error: {result.error}")

asyncio.run(generate_exam())
```

### Integration with Main Agent

You can expose this as a tool in your main agent:

```python
from langchain_core.tools import tool
from workflows.exam_api import exam_api_graph, ExamAPIState

@tool
async def generate_exam_from_pdfs(
    pdf_paths: List[str],
    question_header: str,
    question_description: str,
    api_key: str
) -> str:
    """Generate exam questions from PDF files."""
    state = ExamAPIState(
        pdf_paths=pdf_paths,
        question_header=question_header,
        question_description=question_description,
        api_key=api_key,
    )
    
    result = await exam_api_graph.ainvoke(state)
    return result.generated_questions or result.error
```

## API Requirements

### Endpoint 1: Upload PDFs

```http
POST /api/generate-questions
Content-Type: multipart/form-data

Body:
- file-0: [PDF binary]
- file-1: [PDF binary]
- questionHeader: string
- questionDescription: string
- apiKey: string
- modelName: string (optional)

Response:
{
  "message": "success",
  "uploadedFiles": ["1234567890.pdf", "1234567891.pdf"]
}
```

### Endpoint 2: Generate Questions

```http
GET /api/generate-questions?questionHeader=...&questionDescription=...&apiKey=...&uploadedFiles=file1.pdf,file2.pdf

Content-Type: text/event-stream

Stream:
data: # Generated Exam\n\n
data: ## Question 1\n\n
data: ...\n
data: [DONE]
```

## State Fields

| Field | Type | Description |
|-------|------|-------------|
| `pdf_paths` | `List[str]` | Paths to PDF files |
| `question_header` | `str` | Exam header/title |
| `question_description` | `str` | Requirements for questions |
| `api_key` | `str` | OpenRouter API key |
| `api_base_url` | `str` | API base URL (default: localhost:3000) |
| `model_name` | `str` | Optional AI model name |
| `uploaded_files` | `List[str]` | File IDs from upload response |
| `generated_questions` | `str` | Final markdown output |
| `error` | `str` | Error message if failed |

## Dependencies

```bash
pip install httpx
```

Or with Poetry:

```bash
poetry add httpx
```

## Error Handling

The workflow handles several error cases:

- **File not found**: Returns error if PDF path doesn't exist
- **Upload failure**: Captures HTTP errors from POST request
- **Generation timeout**: 300s timeout for streaming requests
- **SSE errors**: Detects error events in stream

All errors are captured in `state.error` and prevent further execution.

## Streaming

The workflow uses Server-Sent Events (SSE) to handle real-time question generation:

```python
async with client.stream("GET", url, params=params) as response:
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            content = line[6:]  # Extract content
            generated_content.append(content)
```

## Configuration

Set your API details in the state:

```python
state = ExamAPIState(
    api_base_url="https://your-api.com",  # Change from localhost
    api_key=os.getenv("OPENROUTER_API_KEY"),  # Use environment variables
    model_name="anthropic/claude-3-opus",  # Specify model
    # ...
)
```

## Running the Example

```bash
# From project root
python examples/exam_api_example.py
```

Make sure:
1. The API is running at the specified URL
2. PDF paths are valid
3. API key is correct
4. Network connectivity is available
