# Gradent Study Assistant

A multi-agent study coach built on LangGraph + LangChain that connects assignment intelligence, scheduling, progress logging, and proactive nudges in one orchestrated system. The project was developed for a hackathon scenario where Brightspace/LMS data, calendars, and vector-DB resources are ingested and kept fresh by a context updater.

## Highlights

- **Orchestrator agent** (LangChain ReAct) that calls specialized LangGraph workflows as tools.
- **Assignment analysis** workflow that estimates effort, difficulty, risk, milestones, and prerequisites.
- **Scheduler** workflow that coordinates meeting/study blocks with constraints and attendee availability.
- **Progress tracking** workflow that logs study history via natural-language conversations.
- **Suggestions** workflow that synthesizes assignments, study history, calendar context, and resources into actionable reminders.
- **Notification worker** that pushes due suggestions to Discord (and is extensible to other channels).
- **SQLite + SQLAlchemy** relational model covering users, courses, assignments, user-specific progress, study history, and suggestions.
- **Vector store integration** (Chroma) seeded with course resources for retrieval-augmented suggestions.

```
                         ┌──────────────────────────────────────┐
                         │            Main Agent                │
                         │  (LangChain ReAct + tool routing)    │
                         └──────────────┬───────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
┌───────▼────────┐             ┌────────▼────────┐             ┌────────┴────────┐
│Assignment      │             │Scheduler        │             │Suggestions      │
│Assessment      │             │Workflow         │             │Workflow         │
│(LangGraph)     │             │(LangGraph)      │             │(LangGraph)      │
└───────▲────────┘             └────────▲────────┘             └────────▲────────┘
        │                               │                               │
        │                  ┌────────────┴──────────────┐                │
        │                  │Progress Tracking Workflow │                │
        │                  │(LangGraph)                │                │
        │                  └────────────▲──────────────┘                │
        │                               │                               │
        │                    ┌──────────┴───────────┐                   │
        │                    │   SQLite Database    │◄──────────────────┘
        │                    │ assignments, users,  │
        │                    │ user_assignments,    │
        │                    │ study_history, ...   │
        │                    └──────────┬───────────┘
        │                               │
        └───────────────► Vector DB (Chroma) ◄───────────────┐
                                        │                    │
                              Discord Dispatcher      Context Updater
```

## Repository Layout (trimmed)

```
gradent/
├── main.py                         # CLI chat entrypoint
├── main_agent/
│   ├── agent.py                    # ReAct agent setup
│   └── workflow_tools.py           # Tool wrappers for each workflow
├── workflows/
│   ├── assignment_assessment/      # Assignment analysis LangGraph
│   ├── scheduler/                  # Calendar-aware scheduling LangGraph
│   ├── progress_tracking/          # Study logging LangGraph
│   └── suggestions/                # Proactive suggestions LangGraph
├── database/
│   ├── connection.py               # SQLAlchemy session helpers
│   ├── models.py                   # ORM models (users, assignments, etc.)
│   └── mock_data.py                # Mock dataset + helpers
├── notifications/
│   ├── dispatcher.py               # Async worker that delivers due suggestions
│   └── discord.py                  # Discord webhook client
├── setup_mock_data.py              # Clears + seeds the DB with sample data
├── setup_mock_suggestions.py       # Inserts demo suggestions
├── setup_vector_db.py              # Seeds Chroma with course resources
└── workflows/suggestions/README.md # Additional workflow documentation
```

## Data Model at a Glance

Key tables from `database/models.py`:

- `users`, `courses`, `assignments`: LMS-sourced metadata.
- `user_assignments`: per-student status, estimated hours, hours_worked, notes.
- `assignment_assessments`: AI-generated effort/difficulty versions.
- `study_history`: granular logs of study sessions (minutes, focus, quality, notes).
- `study_blocks`: planned sessions (scheduler output).
- `suggestions`: proactive nudges ready for notification channels.

SQLite lives at `data/study_assistant.db` (created on demand).

## Getting Started

1. **Quick Setup (Recommended)**
   ```bash
   # Run the unified setup script - it does everything!
   bash setup.sh
   
   # Or manually:
   poetry install
   poetry run python scripts/setup_all.py
   ```
   
   This will:
   - Install all dependencies
   - Initialize the SQL database schema
   - Populate mock data (users, courses, assignments)
   - Set up the vector database with sample documents
   - Create sample suggestions for testing

2. **Configure environment**
   Create a `.env` file and set:
   ```
   OPENAI_API_KEY=sk-...
   # Optional overrides
   # OPENAI_BASE_URL=https://your-gateway/v1
   # DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   # SUGGESTION_POLL_SECONDS=30
   # SUGGESTION_MAX_PER_CYCLE=1
   ```

3. **Reset data (if needed)**
   ```bash
   # Full reset with confirmation
   poetry run python scripts/setup_all.py --reset
   
   # Or run individual setup scripts
   poetry run python scripts/setup_mock_data.py
   poetry run python scripts/setup_vector_db.py
   ```

4. **Run the CLI assistant**
   ```bash
   poetry run python main.py
   ```
   The agent will automatically call workflows like assignment assessment, scheduling, progress logging, and suggestions based on user intent.

5. **Generate proactive suggestions on demand**
   ```bash
   poetry run python <<'PY'
   import asyncio
   from langchain_core.runnables import RunnableConfig
   from shared.config import Configuration
   from main_agent.workflow_tools import generate_suggestions

   async def main():
       cfg = Configuration(); cfg.validate()
       result = await generate_suggestions.ainvoke(
           {}, config=RunnableConfig(configurable={"openai_api_key": cfg.openai_api_key})
       )
       print(result)

   asyncio.run(main())
   PY
   ```
   Suggestions are persisted to the `suggestions` table and returned as JSON for any UI.

6. **Dispatch notifications (Discord)**
   ```bash
   poetry run python -m notifications.dispatcher
   ```
   The dispatcher polls pending suggestions and posts to the configured Discord webhook. Tweak cadence via `SUGGESTION_POLL_SECONDS` and `SUGGESTION_MAX_PER_CYCLE`.

7. **Run tests**
   ```bash
   poetry run pytest
   ```

## Additional Workflows

- **Assignment Assessment**: `workflows/assignment_assessment/README.md` (structure & prompts).
- **Progress Tracking**: see `workflows/progress_tracking/README.md` for conversation loop examples.
- **Suggestions**: `workflows/suggestions/README.md` covers context gathering and LLM prompts.

Each workflow is a LangGraph graph composed of Pydantic states and async node functions, surfaced to the orchestrator via tools defined in `main_agent/workflow_tools.py`.

## Notifications & Automation

- `notifications/dispatcher.py` can be scheduled (cron/systemd) for continuous delivery.
- `notifications/discord.py` is intentionally minimal—extend it for Slack, email, or SMS by adding new channel clients and toggles in `channel_config`.

## Development Tips

- Use `database/mock_data.populate_mock_data()` to reset the dataset quickly.
- `setup_mock_data.py` prompts before clearing data—handy when switching scenarios.
- Vector embeddings live under `vector_db/`. Regenerate after updating content.
- For progress tracking demos, run `poetry run python tests/test_progress_tracking_conversation.py`.

## License

MIT

## Contributing

Bug reports, feature ideas, and PRs are welcome—especially around new notification channels, Brightspace ingestion, and richer scheduling integrations.
