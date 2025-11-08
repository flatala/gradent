# Gradent - AI Exam Generator

An AI-powered exam generation system with a modern web interface. Upload PDFs, describe your requirements, and get professionally formatted exams in seconds.

## 🌟 Features

- **📄 PDF Processing**: Upload lecture notes, textbooks, or any educational PDFs
- **🤖 AI-Powered**: Uses advanced LLMs (Gemini) via OpenRouter
- **🎨 Modern UI**: Beautiful React interface with drag-and-drop uploads
- **⚡ Real-time Generation**: Streaming responses for immediate feedback
- **📝 LaTeX Support**: Renders mathematical formulas beautifully
- **💾 Export Options**: Download as Markdown or copy to clipboard

## 🚀 Quick Start

### Installation

```bash
# 1. Install backend
poetry install

# 2. Install frontend
cd frontend && npm install && cd ..

# 3. Install Next.js API
cd QuestGen-AI-Agent/code && npm install && cd ../..

# 4. Setup environment
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env
```

### Run Application

```bash
# Easy way (one command):
./start.sh

# Or manually (3 terminals):
# Terminal 1: cd QuestGen-AI-Agent/code && npm run dev
# Terminal 2: python -m app.main
# Terminal 3: cd frontend && npm run dev
```

### Access
- **Web UI**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

**Full guide:** [QUICKSTART.md](QUICKSTART.md)

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Installation and setup
- **[FRONTEND_BACKEND_GUIDE.md](FRONTEND_BACKEND_GUIDE.md)** - Architecture explained
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Visual diagrams
- **[workflows/exam_api/README.md](workflows/exam_api/README.md)** - Workflow details

## 🏗️ Architecture

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-...
```

### 4. Configure Models (Optional)

Edit `model_config.json` to change the models:

```json
{
  "orchestrator_model": "gpt-4o",
  "text_model": "gpt-4o-mini"
}
```

## Usage

### Run the Interactive Chat

```bash
poetry run python main.py
```

Or if using pip:

```bash
python main.py
```

### Example Interactions

**Planning:**
```
You: Help me plan a social media marketing campaign for a new product launch
Assistant: [Invokes planning workflow, may search web and ask questions]
```

**Data Processing:**
```
You: Analyze this customer feedback data: {"reviews": [...], "ratings": [...]}
Assistant: [Invokes data processing workflow to extract insights]
```

**Regular Chat:**
```
You: What's the difference between LangChain and LangGraph?
Assistant: [Responds conversationally without invoking workflows]
```

### CLI Commands

- `quit`, `exit`, `q` - Exit the chat
- `reset` - Clear conversation history
- `help` - Show usage tips

## Key Concepts

### 1. Configuration Pattern

The template uses a shared `Configuration` dataclass:

```python
from shared.config import Configuration

config = Configuration.from_runnable_config(runnable_config)
```

This enables dependency injection across all agents and workflows.

### 2. LLM Factory Functions

Two utility functions provide LLM instances:

```python
from shared.utils import get_orchestrator_llm, get_text_llm

orchestrator = get_orchestrator_llm(config)  # For reasoning
text_llm = get_text_llm(config)              # For generation
```

### 3. Workflow as Tools

Workflows are wrapped as LangChain tools:

```python
@tool
async def run_planning_workflow(query: str, *, config: ...) -> str:
    result = await planning_graph.ainvoke(initial_state, config)
    return json.dumps(result)
```

### 4. Human-in-the-Loop

Workflows can request human input:

```python
from langgraph.types import interrupt

@tool
def human_input(question: str) -> str:
    response = interrupt({"question": question})
    return response.get("data", "")
```

### 5. State Management

Each workflow defines its own Pydantic state model:

```python
class PlanningState(BaseModel):
    query: str
    messages: list = Field(default_factory=list)
    plan: Optional[Plan] = None

    class Config:
        arbitrary_types_allowed = True
```

## Customization

### Adding a New Workflow

1. Create a new directory in `workflows/`:
   ```
   workflows/my_workflow/
   ├── graph.py
   ├── state.py
   ├── nodes.py
   ├── tools.py
   └── prompts.py
   ```

2. Define your state model in `state.py`
3. Implement tools in `tools.py`
4. Create nodes in `nodes.py`
5. Build the graph in `graph.py`
6. Create a tool wrapper in `main_agent/workflow_tools.py`
7. Add the tool to the main agent in `main_agent/agent.py`

### Adding Custom Tools

Define tools using the `@tool` decorator:

```python
from langchain_core.tools import tool, InjectedToolArg
from langchain_core.runnables import RunnableConfig

@tool
async def my_custom_tool(
    param: str,
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Tool description for the LLM."""
    cfg = Configuration.from_runnable_config(config)
    # Your tool logic here
    return result
```

### Modifying Prompts

Edit the prompt files in each workflow:
- `workflows/planning/prompts.py`
- `workflows/data_processing/prompts.py`

## Best Practices

1. **State Design**: Keep state models simple with clear fields
2. **Tool Naming**: Use descriptive names that help the LLM understand when to use them
3. **Prompts**: Provide clear instructions and examples in system prompts
4. **Error Handling**: Wrap tool calls in try/except blocks
5. **Configuration**: Use the config injection pattern for all parameters
6. **Async**: Use async/await throughout for better performance

## Troubleshooting

### "Configuration error: OPENAI_API_KEY environment variable is not set"

Make sure you have a `.env` file with your API key:

```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### Workflows not executing

Check that:
1. Tools are properly registered in `main_agent/agent.py`
2. Tool descriptions clearly indicate when to use them
3. The agent has permission to use tools (check `verbose=True` output)

### Human-in-the-loop not working

The current implementation returns "WORKFLOW_NEEDS_INPUT" messages. To fully implement:
1. Detect these messages in the main agent
2. Prompt the user for input
3. Resume the workflow with the user's response using `Command(resume=...)`

## License

MIT

## Contributing

Feel free to fork and customize this template for your needs!
