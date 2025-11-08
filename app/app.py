from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List

# Ensure project root is importable before importing local modules
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import chainlit as cl

from database.connection import get_db_session
from database.models import Suggestion, SuggestionStatus, User
from shared.config import Configuration
from main_agent import MainAgent


def _build_config():
    """Create LangChain runnable config with Chainlit callbacks."""
    callback = cl.LangchainCallbackHandler()
    return {
        "callbacks": [callback],
        "configurable": {"thread_id": cl.context.session.id},
    }


def _get_default_user_id() -> int | None:
    with get_db_session() as db:
        record = db.query(User.id).order_by(User.id.asc()).first()
        return record[0] if record else None


def _fetch_active_suggestions(user_id: int) -> List[Dict]:
    with get_db_session() as db:
        rows: List[Suggestion] = (
            db.query(Suggestion)
            .filter(
                Suggestion.user_id == user_id,
                Suggestion.status.in_(
                    [SuggestionStatus.PENDING, SuggestionStatus.NOTIFIED]
                ),
            )
            .order_by(Suggestion.created_at.desc())
            .all()
        )

        serialized: List[Dict] = []
        for row in rows:
            serialized.append(
                {
                    "id": row.id,
                    "title": row.title,
                    "message": row.message,
                    "category": row.category,
                    "priority": row.priority or "medium",
                    "suggested_time": (
                        row.suggested_time.isoformat() if row.suggested_time else None
                    ),
                    "suggested_time_text": row.suggested_time_text,
                }
            )

        return serialized


def _format_suggestions_message(suggestions: List[Dict]) -> str:
    if not suggestions:
        cl.user_session.set("suggestion_index_map", {})
        return ""

    lines = ["Here are your latest suggestions:"]
    index_map: Dict[int, int] = {}
    for idx, suggestion in enumerate(suggestions, start=1):
        when = (
            suggestion["suggested_time_text"]
            or (
                suggestion["suggested_time"]
                if suggestion["suggested_time"]
                else "Soon"
            )
        )
        lines.append(
            f"{idx}) {suggestion['title']}\n"
            f"- {suggestion['message']}\n"
            f"- When: {when}\n"
            f"- Priority: {suggestion['priority']}"
        )
        index_map[idx] = suggestion["id"]

    cl.user_session.set("suggestion_index_map", index_map)
    lines.append(
        "\nUse `/done <number>` to mark a suggestion complete or `/dismiss <number>` to hide it."
    )
    return "\n\n".join(lines)


def _update_suggestion_status(suggestion_id: int, status: SuggestionStatus) -> bool:
    updated = False
    with get_db_session() as db:
        suggestion = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
        if suggestion:
            suggestion.status = status
            suggestion.updated_at = datetime.utcnow()
            updated = True
    return updated


@cl.on_chat_start
async def handle_start():
    """Initialize the LangGraph main agent when a session begins."""
    try:
        cfg = Configuration()
        cfg.validate()
    except ValueError as exc:
        await cl.Message(
            author="system",
            content=f"Configuration error: {exc}",
            type="error",
        ).send()
        return

    agent = MainAgent(cfg)
    cl.user_session.set("agent", agent)
    await cl.Message(
        author="assistant",
        content="Hi! I’m ready to help with planning, assignments, and scheduling.",
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Forward user messages to the LangGraph agent and return its response."""
    agent: MainAgent | None = cl.user_session.get("agent")
    if agent is None:
        await handle_start()
        agent = cl.user_session.get("agent")
        if agent is None:
            await cl.Message(
                author="system",
                content="Agent failed to initialize. Please check server logs.",
                type="error",
            ).send()
            return

    # Handle suggestion management commands
    content_lower = message.content.strip().lower()
    index_map = cl.user_session.get("suggestion_index_map") or {}

    msg = cl.Message(author="assistant", content="")
    try:
        response_text = await agent.chat(
            message.content,
            config=_build_config(),
        )
        await msg.stream_token(response_text)
    except Exception as exc:  # pragma: no cover - best effort error surface
        await cl.Message(
            author="system",
            content=f"Error while generating response: {exc}",
            type="error",
        ).send()
        return

    await msg.send()


@cl.on_chat_end
async def handle_end():
    """Clear chat state when the session closes."""
    agent: MainAgent | None = cl.user_session.get("agent")
    if agent:
        agent.reset_history()