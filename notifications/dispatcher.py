"""Simple scheduler that dispatches due suggestions to notification channels."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import os

from sqlalchemy import or_

from database.connection import get_db_session
from database.models import Suggestion, SuggestionStatus
from notifications.discord import send_discord_notification

POLL_SECONDS = int(os.getenv("SUGGESTION_POLL_SECONDS", "10"))
MAX_PER_CYCLE = int(os.getenv("SUGGESTION_MAX_PER_CYCLE", "1"))


def dispatch_once() -> int:
    """Dispatch due suggestions once. Returns count sent."""
    now = datetime.utcnow()
    sent = 0

    with get_db_session() as db:
        due: list[Suggestion] = (
            db.query(Suggestion)
            .filter(
                Suggestion.status == SuggestionStatus.PENDING,
                or_(
                    Suggestion.suggested_time.is_(None),
                    Suggestion.suggested_time <= now,
                ),
            )
            .order_by(Suggestion.created_at.asc())
            .limit(MAX_PER_CYCLE)
            .all()
        )

        for suggestion in due:
            channel_config = suggestion.channel_config or {}
            delivered = False

            if channel_config.get("discord"):
                delivered = send_discord_notification(suggestion)

            suggestion.status = SuggestionStatus.NOTIFIED
            suggestion.last_notified_at = datetime.utcnow()
            suggestion.times_notified = (suggestion.times_notified or 0) + 1

            if delivered:
                suggestion.delivered_at = datetime.utcnow()
                sent += 1

    return sent


async def run_scheduler():
    """Continuously dispatch suggestions on an interval."""
    interval = max(POLL_SECONDS, 10)
    while True:
        dispatch_once()
        await asyncio.sleep(interval)


if __name__ == "__main__":
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        pass

