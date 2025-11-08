# Suggestions Workflow

The suggestions pipeline produces proactive “next best action” messages based on the latest state of assignments, calendar events, study history, and newly ingested resources. It is meant to complement the scheduler and assignment agents by highlighting urgent tasks, reinforcing weak areas, and filling open time blocks with useful work.

## Overview

```
Context Updater / DB → Suggestions Workflow (LangGraph) → LangChain Tool `generate_suggestions` → Orchestrator / UI
```

1. **collect_context (`nodes.py`)**  
   Queries the database for the target user (default: first user in the `users` table) and assembles:
   - Assignments bucketed into `overdue`, `due_soon` (≤7 days), and `later`, including the latest `AssignmentAssessment`.
   - Calendar gaps (still mocked today; ready for real calendar integration).
   - Study-history / spaced-repetition signals pulled from the `study_history` table (latest 20 entries, joined with assignments and courses).
   - Resource matches by linking mock assignment documents from `vector_db/mock_documents.py`.

2. **generate_suggestions_node (`nodes.py`)**  
   Sends the context to the text LLM using prompts defined in `prompts.py`. The model must return a JSON array of up to five suggestions using the schema in `Suggestion` (category, message, priority, linked IDs, etc.). If parsing fails, the workflow emits a single fallback suggestion explaining the error.

3. **suggestions_graph (`graph.py`)**  
   Simple two-step LangGraph pipeline:
   - `collect_context` → `generate_suggestions`
   - Output: populated `SuggestionsState.suggestions`

4. **LangChain tool (`main_agent/workflow_tools.py`)**  
   - `generate_suggestions(user_id: Optional[int])` wraps the graph and returns a JSON string.  
   - Defaults to the first user if `user_id` is omitted.  
   - Persists each suggestion to the `suggestions` SQL table (idempotent upsert) with channel flags for downstream notifiers (e.g., Discord).  
   - Logs tool calls and handles errors gracefully.

5. **Orchestrator integration (`main_agent/agent.py` & `prompts.py`)**  
   - The tool is registered alongside planning and assignment analysis.  
   - The system prompt instructs the orchestrator to call it when the user asks for reminders / next steps or when new data arrives.

6. **Notification surfaces**  
   - CLI / orchestrator responses return structured JSON so you can surface suggestions in any UI.  
   - Discord delivery is handled by `notifications/dispatcher.py` (polling worker) + `notifications/discord.py` webhook helper.  
   - Suggestion lifecycle tracked via `SuggestionStatus` (`pending` → `notified` → `completed`/`dismissed`).

## Data Requirements

Populate the SQLite database via `database/mock_data.py` (or your ingestion pipeline) so the workflow has:
- `users`, `courses`, `assignments`
- `assignment_assessments` (latest versions flagged `is_latest=True`)

Study history is read directly from `study_history` (joined via `user_assignments` / `assignments`).  
Calendar events are still mocked; replace `_mock_calendar_gaps` in `nodes.py` once those tables exist.

## Running Locally

1. Seed the DB:
   ```bash
   poetry run python -m database.mock_data
   ```
2. Invoke the tool directly:
   ```bash
   poetry run python <<'PY'
   import asyncio
   from langchain_core.runnables import RunnableConfig
   from shared.config import Configuration
   from main_agent.workflow_tools import generate_suggestions

   async def main():
       cfg = Configuration()
       cfg.validate()
       response = await generate_suggestions.ainvoke(
           {},
           config=RunnableConfig(configurable={"openai_api_key": cfg.openai_api_key})
       )
       print(response)

   asyncio.run(main())
   PY
   ```
3. Surface the suggestions however you like (e.g., via the main agent CLI). The JSON returned from step 2 is persisted to the database and ready for downstream consumers.

4. (Optional) Start the Discord dispatcher in another terminal (default sends one notification per cycle):
   ```bash
   poetry run python -m notifications.dispatcher
   ```
   The worker polls every 60 seconds (configurable via `SUGGESTION_POLL_SECONDS`) and pushes due suggestions to the Discord webhook defined in `DISCORD_WEBHOOK_URL`.  
   To throttle delivery, adjust `SUGGESTION_MAX_PER_CYCLE` (defaults to `1`) so only a single notification goes out each poll.

## File Structure

- `state.py` – Defines `SuggestionsState` and the `Suggestion` model.
- `nodes.py` – Context gathering and LLM invocation nodes.
- `prompts.py` – System + instruction prompts guiding the LLM output.
- `graph.py` – Compiled LangGraph workflow.
- `README.md` – (this file) documentation and usage notes.
- `notifications/discord.py` – Helper to send suggestions to Discord via webhook.
- `notifications/dispatcher.py` – Minimal asyncio scheduler that polls and delivers due suggestions.

## Extending the Workflow

- Replace the placeholder calendar helper with a real query or calendar API integration.
- Add richer scheduling: parse natural-language times, respect user quiet hours, support snooze/reschedule.
- Expand categories (wellness, collaboration prompts) and update the prompt schema accordingly.
- Integrate additional channels (email/SMS) by adapting the dispatcher and channel config.

