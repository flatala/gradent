# Quick Start: Exam API Workflow

## Installation

1. **Install dependencies:**
   ```bash
   poetry install
   # or
   pip install httpx
   ```

2. **Set up environment variables:**
   ```bash
   echo "OPENROUTER_API_KEY=your-key-here" >> .env
   ```

## Standalone Usage

```python
import asyncio
from workflows.exam_api import exam_api_graph, ExamAPIState

async def main():
    state = ExamAPIState(
        pdf_paths=["lecture1.pdf", "lecture2.pdf"],
        question_header="Final Exam - Mathematics 301",
        question_description="""
        Generate 20 questions:
        - 15 multiple choice (5 easy, 7 medium, 3 hard)
        - 5 problem-solving (all hard)
        Focus on: calculus, linear algebra, probability
        """,
        api_key="your-api-key",
    )
    
    result = await exam_api_graph.ainvoke(state)
    print(result.generated_questions)

asyncio.run(main())
```

## Integration with Main Agent

Add the tool to your agent's available tools:

```python
# In main_agent/agent.py
from main_agent.exam_api_tool import run_exam_api_workflow

tools: List[BaseTool] = [
    run_planning_workflow,
    run_exam_api_workflow,  # Add this
]
```

Then users can ask:
- "Generate an exam from my calculus notes PDF"
- "Create 10 practice questions from lecture_slides.pdf"
- "Make a midterm test with 20 questions from my materials"

## Testing the API Connection

Quick test to verify the API is working:

```python
import asyncio
import httpx

async def test_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:3000/api/health")
        print(f"API Status: {response.status_code}")

asyncio.run(test_api())
```

## Common Issues

### API not responding
- Ensure the API server is running
- Check `api_base_url` is correct
- Verify firewall/network settings

### PDF upload fails
- Check file paths are absolute
- Verify PDFs are readable
- Check file size limits

### No questions generated
- Verify API key is valid
- Check PDF content is extractable
- Review question_description format

## Next Steps

1. ✅ Test standalone workflow
2. ✅ Integrate with main agent
3. ✅ Add error handling for your use case
4. ✅ Customize question generation prompts
5. ✅ Add output formatting/post-processing
