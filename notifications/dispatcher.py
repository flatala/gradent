"""Simple scheduler that dispatches due suggestions to notification channels."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import os

from sqlalchemy import or_

from database.connection import get_db_session
from database.models import Suggestion, SuggestionStatus
from notifications.discord import send_discord_notification
from notifications.autonomous import send_ntfy_notification

POLL_SECONDS = int(os.getenv("SUGGESTION_POLL_SECONDS", "10"))
MAX_PER_CYCLE = int(os.getenv("SUGGESTION_MAX_PER_CYCLE", "1"))

# Global config for ntfy (can be set by main app)
_ntfy_topic = None

def set_ntfy_topic(topic: str):
    """Set the global ntfy topic for dispatcher notifications."""
    global _ntfy_topic
    _ntfy_topic = topic


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

            # Try Discord notification
            if channel_config.get("discord"):
                delivered = send_discord_notification(suggestion)

            # ALSO try ntfy notification if topic is configured
            if _ntfy_topic:
                try:
                    category = (suggestion.category or "suggestion").replace("_", " ").title()
                    deadline_text = (
                        suggestion.suggested_time_text
                        or (
                            suggestion.suggested_time.strftime("%b %d %Y %H:%M")
                            if suggestion.suggested_time
                            else "Soon"
                        )
                    )
                    
                    message = f"{suggestion.title}\n\n{suggestion.message or 'No details'}\n\nDeadline: {deadline_text}"
                    
                    # Run async function in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ntfy_success = loop.run_until_complete(
                        send_ntfy_notification(
                            message=message,
                            topic=_ntfy_topic,
                            title=f"💡 {category}: {suggestion.title}",
                            priority=4,
                            tags=["bulb", "calendar"]
                        )
                    )
                    loop.close()
                    
                    if ntfy_success:
                        delivered = True
                except Exception as e:
                    print(f"Failed to send ntfy notification: {e}")

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

