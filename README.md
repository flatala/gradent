# Gradent Study Assistant

A multi-agent study coach built on LangGraph + LangChain that connects assignment intelligence, scheduling, progress logging, and proactive nudges in one orchestrated system. The project features both a conversational chat interface and an autonomous executor for background automation. Integrated with LMS data (Like Brightspace or Canvas), google calendar. Vector-DB resources are ingested and kept fresh by a context updater.

## Highlights

- **Chat Agent** (LangChain ReAct) for conversational interaction with users that calls specialized LangGraph workflows as tools.
- **Executor Agent** for autonomous background tasks (cron jobs, webhooks, event-driven automation) without user interaction.
- **Assignment Assessment** workflow that estimates effort, difficulty, risk, milestones, and prerequisites.
- **Scheduler** workflow that coordinates meeting/study blocks with constraints, attendee availability, and Google Calendar integration.
- **Progress Tracking** workflow that logs study history via natural-language conversations.
- **Suggestions** workflow that synthesizes assignments, study history, calendar context, and resources into actionable reminders.
- **Exam API** workflow that generates practice exams from PDF materials with MathJax formatting.
- **Full-stack application** with FastAPI backend and React frontend (shadcn/ui).
- **Notification worker** that pushes due suggestions to Discord (extensible to other channels).
- **SQLite + SQLAlchemy** relational model covering users, courses, assignments, user-specific progress, study history, and suggestions.
- **Vector store integration** (Chroma) seeded with course resources for retrieval-augmented suggestions.

```
                         ┌──────────────────────────────────────┐
                         │         Chat Agent                   │
                         │  (LangChain ReAct + conversational)  │
                         └──────────────┬───────────────────────┘
                                        │
        ┌───────────────────────────────┼──────────────────────────────────────┐
        │                               │                                      │
        │                   ┌───────────▼────────────┐                         │
        │                   │   Executor Agent       │                         │
        │                   │ (autonomous/background)│                         │
        │                   └───────────┬────────────┘                         │
        │                               │                                      │
        │       ┌───────────────────────┼───────────────────────┐              │
        │       │                       │                       │              │
┌───────▼───────▼──┐           ┌────────▼────────┐      ┌──────▼──────┐      │
│Assignment        │           │Scheduler        │      │Suggestions  │      │
│Assessment        │           │Workflow         │      │Workflow     │      │
│(LangGraph)       │           │(LangGraph)      │      │(LangGraph)  │      │
└───────▲──────────┘           └────────▲────────┘      └──────▲──────┘      │
        │                               │                      │              │
        │                  ┌────────────┴──────────────┐       │              │
        │                  │Progress Tracking Workflow │       │              │
        │                  │(LangGraph)                │       │              │
        │                  └────────────▲──────────────┘       │              │
        │                               │                      │              │
        │                  ┌────────────┴──────────────┐       │              │
        │                  │   Exam API Workflow       │       │              │
        │                  │   (LangGraph)             │       │              │
        │                  └────────────▲──────────────┘       │              │
        │                               │                      │              │
        │                    ┌──────────┴───────────┐          │              │
        │                    │   SQLite Database    │◄─────────┴──────────────┘
        │                    │ assignments, users,  │
        │                    │ user_assignments,    │
        │                    │ study_history, ...   │
        │                    └──────────┬───────────┘
        │                               │
        └───────────────► Vector DB (Chroma) ◄───────────────┐
                                        │                    │
                              Discord Dispatcher      Context Updater
                                        │                    │
                                        └────────────────────┘
                                        Brightspace LMS API
```

## Architecture Overview

### Two Main Agents

1. **Chat Agent** (`agents/chat_agent/`)
   - Conversational ReAct agent for user interaction
   - Natural language understanding and tool routing
   - Multi-turn dialogue with conversation history
   - Exposes workflows as tools for user queries

2. **Executor Agent** (`agents/executor_agent/`)
   - Autonomous agent for background tasks
   - No user interaction - fully automated
   - Designed for cron jobs, webhooks, event triggers
   - Returns structured results for monitoring
   - Use cases: LMS sync, auto-assessments, scheduled suggestions

### Five Task Agent Workflows (LangGraph)

Each workflow is a complete LangGraph graph with state management, nodes, and prompts:

1. **Assignment Assessment** (`agents/task_agents/assignment_assessment/`)
   - AI analysis of assignment difficulty and effort
   - Generates milestones and prerequisites
   - Provides low/most/high hour estimates

2. **Scheduler** (`agents/task_agents/scheduler/`)
   - Google Calendar integration with OAuth
   - Availability checking and conflict resolution
   - Creates events with Google Meet links
   - Supports time preferences and attendees

3. **Progress Tracking** (`agents/task_agents/progress_tracking/`)
   - Conversational study session logging
   - Natural language duration parsing
   - Focus and quality ratings (1-5 scale)
   - Multi-turn conversation for missing information

4. **Suggestions** (`agents/task_agents/suggestions/`)
   - Proactive study recommendations
   - Analyzes assignments, calendar, study history
   - RAG integration with vector database
   - Priority-based actionable suggestions

5. **Exam API** (`agents/task_agents/exam_api/`)
   - Generates practice exams from PDF materials
   - External API integration (OpenRouter)
   - MathJax-formatted questions
   - Streaming response support

## Repository Layout

```
langgraph-template/
├── main.py                              # CLI chat entrypoint
├── start.sh                             # Quick start script (all services)
├── setup.sh                             # Initial setup script
├── pyproject.toml                       # Python dependencies (Poetry)
├── .env.example                         # Environment configuration template
│
├── agents/
│   ├── chat_agent/                      # Conversational ReAct agent
│   │   ├── agent.py                     # Main chat agent logic
│   │   └── prompts.py                   # System prompts
│   │
│   ├── executor_agent/                  # Autonomous background agent
│   │   ├── executor.py                  # Executor logic
│   │   └── prompts.py                   # Task prompts
│   │
│   ├── task_agents/                     # LangGraph workflows
│   │   ├── assignment_assessment/       # Assignment analysis
│   │   ├── scheduler/                   # Calendar-aware scheduling
│   │   ├── progress_tracking/           # Study logging
│   │   ├── suggestions/                 # Proactive recommendations
│   │   └── exam_api/                    # Exam generation
│   │
│   └── shared/
│       └── workflow_tools.py            # Tool wrappers for workflows
│
├── app/
│   └── main.py                          # FastAPI backend (port 8000)
│
├── frontend/                            # React + Vite + shadcn/ui
│   ├── src/                             # TypeScript source
│   ├── package.json                     # Node.js dependencies
│   └── vite.config.ts                   # Vite configuration
│
├── database/
│   ├── connection.py                    # SQLAlchemy session helpers
│   ├── models.py                        # ORM models (users, assignments, etc.)
│   └── mock_data.py                     # Mock dataset + helpers
│
├── context_updater/
│   ├── brightspace_client.py            # Brightspace API client (mock)
│   └── ingestion.py                     # LMS sync to database
│
├── notifications/
│   ├── dispatcher.py                    # Async worker for suggestions
│   ├── discord.py                       # Discord webhook client
│   └── autonomous.py                    # Notification orchestration
│
├── scripts/
│   ├── setup_all.py                     # Comprehensive setup
│   ├── setup_mock_data.py               # Database seeding
│   ├── setup_vector_db.py               # Vector DB initialization
│   └── rebuild_database.py              # Database migration
│
├── shared/
│   ├── config.py                        # Configuration management
│   ├── utils.py                         # Helper functions
│   └── google_calendar.py               # Google Calendar integration
│
├── vector_db/                           # Chroma vector store
│   └── [course materials embeddings]
│
├── data/
│   └── study_assistant.db               # SQLite database
│
└── tests/                               # Test suite
```

## Tech Stack

### Backend (Python)
- **Framework:** FastAPI (REST API on port 8000)
- **Agent Framework:** LangChain + LangGraph
- **LLM Provider:** OpenAI (configurable base URL)
- **Database:** SQLite + SQLAlchemy ORM
- **Vector DB:** ChromaDB (for RAG)
- **Package Manager:** Poetry
- **Python Version:** >=3.11, <3.14

### Frontend (JavaScript/TypeScript)
- **Framework:** React 18
- **Build Tool:** Vite
- **UI Library:** shadcn/ui (Radix UI components)
- **Styling:** Tailwind CSS
- **Router:** React Router v6
- **State Management:** TanStack Query
- **Markdown:** react-markdown with KaTeX (math support)
- **Package Manager:** npm

### External Integrations
- **Google Calendar API** - Meeting scheduling with OAuth
- **Discord Webhooks** - Notifications
- **Brightspace LMS** - Course/assignment sync (mocked)
- **OpenRouter API** - Exam generation

## Data Model at a Glance

Key tables from `database/models.py`:

- `users`, `courses`, `assignments`: LMS-sourced metadata.
- `user_assignments`: per-student status, estimated hours, hours_worked, notes.
- `assignment_assessments`: AI-generated effort/difficulty versions.
- `study_history`: granular logs of study sessions (minutes, focus, quality, notes).
- `study_blocks`: planned sessions (scheduler output).
- `suggestions`: proactive nudges ready for notification channels.
- `calendar_events`: created calendar events with Google Meet links.
- `exam_results`: practice exam scores and performance tracking.

SQLite database lives at `data/study_assistant.db` (created on demand).

## Getting Started

### Quick Setup (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd langgraph-template

# 2. Run setup script (installs dependencies, creates DB, seeds data)
./setup.sh

# 3. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Environment Configuration

Create a `.env` file with:

```bash
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional overrides:
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_TIMEOUT=60
# OPENAI_MAX_RETRIES=1

# For exam generation:
# OPENROUTER_API_KEY=sk-your-openrouter-api-key

# For notifications:
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
# SUGGESTION_POLL_SECONDS=30
# SUGGESTION_MAX_PER_CYCLE=1

# For Google Calendar (optional):
# Set up OAuth credentials and place credentials.json in project root
```

### Running the Application

#### Option 1: CLI Interface (Chat Agent)

```bash
# Basic usage
poetry run python main.py

# With logging
poetry run python main.py --log --log-level debug
```

The CLI provides an interactive chat interface where you can:
- Schedule meetings and study sessions
- Log study progress conversationally
- Get assignment assessments
- Request proactive suggestions
- Generate practice exams

#### Option 2: Full Stack (Backend + Frontend)

```bash
# Start all services at once
./start.sh

# This launches:
# - Backend API: http://localhost:8000
# - Frontend UI: http://localhost:5173
# - API Documentation: http://localhost:8000/docs
```

#### Option 3: Individual Components

```bash
# Backend only (FastAPI server)
poetry run python -m app.main

# Frontend only (React dev server)
cd frontend && npm install && npm run dev

# Notification dispatcher (autonomous suggestions)
poetry run python -m notifications.dispatcher
```

### Google Calendar Setup (Optional)

For the scheduler workflow to create calendar events:

1. Create a Google Cloud project and enable Calendar API
2. Download OAuth credentials as `credentials.json`
3. Place in project root
4. First run will open browser for OAuth consent
5. Token saved to `token.json` for future use

## Deployment

Deploy the full stack (backend + frontend) using Docker. For detailed docs, see the `deployment/` directory.

- Prerequisites
  - Docker and Docker Compose installed
  - Ubuntu 20.04+ VM recommended for production

- Quick Deploy (automated)
  - Full VM setup (installs Docker, configures firewall, clones and deploys):
    ```bash
    curl -o deploy-vm.sh https://raw.githubusercontent.com/flatala/gradent/main/deploy-vm.sh \
      && chmod +x deploy-vm.sh \
      && ./deploy-vm.sh
    ```
  - If you’ve already cloned this repo on your server:
    ```bash
    chmod +x deployment/deploy.sh
    ./deployment/deploy.sh
    ```

- Manual Docker Compose
  ```bash
  # Configure environment
  cp .env.example .env
  nano .env   # set OPENAI_API_KEY

  # Build and start
  docker compose up -d --build

  # (Optional) initialize database with mock data
  docker compose exec backend python scripts/setup_all.py
  ```

  - Access
    - Frontend: http://your-host/
    - Backend API: http://your-host:8000
    - API Docs: http://your-host:8000/docs
  - Persistent data: `data/`, `logs/`, `uploads/` are mounted into the backend container

- Production (SSL/HTTPS)
  - Obtain certificates with Certbot
  - Update `deployment/nginx-ssl.conf` with your domain
  - Start with production overrides:
    ```bash
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    ```

- Makefile shortcuts
  - `make build`, `make up`, `make logs`, `make status`, `make down`
  - `make prod-up` to run with SSL overrides
  - `make update` to pull, rebuild, and restart

- More docs
  - deployment/README.md
  - deployment/QUICKSTART.md
  - deployment/DEPLOYMENT_GUIDE.md

## Workflow Examples

### Using the Chat Agent

```bash
poetry run python main.py
```

Example conversations:
- "Schedule a study session for CS 301 tomorrow at 2pm"
- "I just studied calculus for 90 minutes, focused really well"
- "Assess the difficulty of my Database Systems project"
- "Give me some study suggestions for this week"
- "Generate a practice exam for Chapter 5"

### Using the Executor Agent

For autonomous background operations:

```python
import asyncio
from agents.executor_agent import ExecutorAgent
from shared.config import Configuration

async def main():
    config = Configuration()
    config.validate()

    executor = ExecutorAgent(config)

    # Run context update + auto-assess + suggestions
    result = await executor.run_context_update_and_assess(
        user_id=1,
        auto_schedule=True
    )

    print(f"Success: {result['success']}")
    print(f"Duration: {result['duration_ms']}ms")

asyncio.run(main())
```

Perfect for cron jobs:
```bash
# Add to crontab for daily LMS sync
0 6 * * * cd /path/to/project && poetry run python -c "import asyncio; from agents.executor_agent import ExecutorAgent; from shared.config import Configuration; c = Configuration(); asyncio.run(ExecutorAgent(c).run_context_update_and_assess(1))"
```

### Generate Suggestions Programmatically

```python
import asyncio
from langchain_core.runnables import RunnableConfig
from shared.config import Configuration
from agents.shared.workflow_tools import generate_suggestions

async def main():
    cfg = Configuration()
    cfg.validate()

    result = await generate_suggestions.ainvoke(
        {},
        config=RunnableConfig(configurable={"openai_api_key": cfg.openai_api_key})
    )
    print(result)

asyncio.run(main())
```

Suggestions are persisted to the `suggestions` table with status tracking.

### Notification Dispatcher

Run the autonomous notification worker:

```bash
poetry run python -m notifications.dispatcher
```

The dispatcher:
- Polls for pending suggestions at configured intervals
- Delivers via Discord webhook (extensible to Slack, email, SMS)
- Updates suggestion status to prevent duplicates
- Configurable via `SUGGESTION_POLL_SECONDS` and `SUGGESTION_MAX_PER_CYCLE`

## Database Management

### Complete Setup (one command)

Run a single script to set up everything for development: reset the SQL DB, seed mock data, populate the vector DB, and create sample suggestions.

```bash
# Run interactive setup (prompts for reset)
poetry run python scripts/setup_all.py

# Start fresh (clears existing DB and vector DB)
poetry run python scripts/setup_all.py --reset
```

### Seed Mock Data

```bash
# Interactive reset with prompts
poetry run python scripts/setup_mock_data.py

# Or use the function directly
poetry run python -m database.mock_data
```

This creates sample users, courses, assignments, and study history. For a full end‑to‑end setup (including vector DB and sample suggestions), use the "Complete Setup" script above.

### Populate Vector Database

```bash
poetry run python scripts/setup_vector_db.py
```

Seeds ChromaDB with course materials for RAG-powered suggestions.

### Rebuild Database Schema

```bash
poetry run python scripts/rebuild_database.py
```

Drops and recreates all tables (destructive).

## Testing

### Run All Tests

```bash
poetry run pytest
```

### Test Specific Workflow

```bash
# Progress tracking conversation
poetry run python tests/test_progress_tracking_conversation.py

# Exam integration
poetry run python scripts/check_exam_integration.py
```

## Additional Workflow Documentation

Each task agent has detailed documentation:

- **Assignment Assessment**: `agents/task_agents/assignment_assessment/README.md`
- **Progress Tracking**: `agents/task_agents/progress_tracking/README.md`
- **Suggestions**: `agents/task_agents/suggestions/README.md`
- **Scheduler**: `agents/task_agents/scheduler/README.md`
- **Exam API**: `agents/task_agents/exam_api/README.md`

Each workflow is a LangGraph graph composed of:
- **state.py** - Pydantic state model
- **graph.py** - LangGraph workflow definition
- **nodes.py** - Node implementation functions
- **prompts.py** - LLM prompts
- **tools.py** - Agent-specific tools (optional)

All workflows are exposed as LangChain tools in `agents/shared/workflow_tools.py`.

## Development Tips

### Configuration Management

The project uses dependency injection via `shared/config.py`:

```python
from shared.config import Configuration

config = Configuration.from_runnable_config(config)
```

Model configuration is in `model_config.json`:
```json
{
  "orchestrator_model": "gpt-4o",
  "text_model": "gpt-4o-mini"
}
```

### Database Session Pattern

Always use context manager for database operations:

```python
from database.connection import get_db_session

with get_db_session() as db:
    # Your database operations
    user = db.query(User).filter_by(id=1).first()
```

### Adding New Workflows

1. Create directory in `agents/task_agents/<workflow_name>/`
2. Implement `state.py`, `graph.py`, `nodes.py`, `prompts.py`
3. Export graph in `__init__.py`
4. Add tool wrapper in `agents/shared/workflow_tools.py`
5. Register tool with chat_agent and/or executor_agent

### Extending Notifications

To add new channels (Slack, email, SMS):

1. Create client in `notifications/<channel>.py`
2. Add channel config to notification orchestration
3. Update `notifications/dispatcher.py` to support new channel
4. Add environment variables for credentials

## API Documentation

When running the backend server, interactive API docs are available:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

The API provides endpoints for:
- Chat conversations
- Workflow execution
- Assignment management
- Study progress tracking
- Suggestion generation
- Exam generation

## License

MIT

## Contributing

Bug reports, feature ideas, and PRs are welcome—especially around:
- New notification channels
- Additional LMS integrations (Canvas, Moodle, etc.)
- Enhanced scheduling algorithms
- More workflow types (flashcard generation, quiz creation, etc.)
- Frontend improvements and mobile support
