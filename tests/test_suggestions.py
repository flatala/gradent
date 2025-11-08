import importlib
import json
from datetime import datetime, timedelta

import pytest


@pytest.mark.asyncio
async def test_generate_suggestions_persists(temp_database, monkeypatch):
    """The suggestions tool should store structured suggestions in SQL."""
    from database import mock_data

    importlib.reload(mock_data)
    mock_data.populate_mock_data()

    from main_agent import workflow_tools

    importlib.reload(workflow_tools)

    from workflows.suggestions.state import Suggestion as SuggestionModel

    async def fake_graph_invoke(state, config):
        return {
            "suggestions": [
                SuggestionModel(
                    title="Start MDP assignment reading",
                    message="Review the assignment doc to refresh notation.",
                    category="deadline_reminder",
                    priority="high",
                    suggested_time="2030-01-01T12:00:00",
                    linked_assignments=[1],
                    linked_events=[],
                    tags=["mdp"],
                    sources=["rl_mdp_assignment"],
                )
            ]
        }

    monkeypatch.setattr(workflow_tools.suggestions_graph, "ainvoke", fake_graph_invoke)

    result_json = await workflow_tools.generate_suggestions.ainvoke(
        {},
        config={"configurable": {"openai_api_key": "test-key"}},
    )
    parsed = json.loads(result_json)
    assert len(parsed) == 1
    assert parsed[0]["title"] == "Start MDP assignment reading"

    from database.connection import get_db_session
    from database.models import Suggestion, SuggestionStatus

    with get_db_session() as db:
        rows = db.query(Suggestion).all()
        assert len(rows) == 1
        stored = rows[0]
        assert stored.status == SuggestionStatus.PENDING
        assert stored.priority == "high"


def test_dispatcher_marks_notified(temp_database, monkeypatch):
    """Dispatcher should notify and transition suggestion status."""
    from database.connection import get_db_session
    from database.models import Suggestion, SuggestionStatus

    due_time = datetime.utcnow() - timedelta(minutes=5)

    with get_db_session() as db:
        suggestion = Suggestion(
            user_id=1,
            title="Reminder",
            message="Finish the report.",
            category="deadline_reminder",
            priority="medium",
            suggested_time=due_time,
            status=SuggestionStatus.PENDING,
            channel_config={"discord": True},
        )
        db.add(suggestion)
        db.flush()
        suggestion_id = suggestion.id

    from notifications import dispatcher

    importlib.reload(dispatcher)

    called = {}

    def fake_send(suggestion):
        called["id"] = suggestion.id
        return True

    monkeypatch.setattr("notifications.dispatcher.send_discord_notification", fake_send)

    count = dispatcher.dispatch_once()
    assert count == 1

    with get_db_session() as db:
        stored = db.query(Suggestion).filter(Suggestion.id == suggestion_id).one()
        assert stored.status == SuggestionStatus.NOTIFIED
        assert stored.times_notified == 1
        assert "id" in called and called["id"] == suggestion_id

