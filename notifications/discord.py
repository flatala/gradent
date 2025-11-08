"""Discord notification helpers."""
from __future__ import annotations

import os
import textwrap
from typing import Optional

import requests

from database.models import Suggestion


def send_discord_notification(suggestion: Suggestion, webhook_url: Optional[str] = None) -> bool:
    """Send a suggestion to a Discord webhook channel.

    Args:
        suggestion: database Suggestion row
        webhook_url: optional override webhook URL; defaults to env DISCORD_WEBHOOK_URL

    Returns:
        bool indicating success
    """
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        from dotenv import load_dotenv

        load_dotenv()
        url = os.getenv("DISCORD_WEBHOOK_URL")
        if not url:
            return False

    category = (suggestion.category or "suggestion").replace("_", " ").title()
    deadline_text = (
        suggestion.suggested_time_text
        or (
            suggestion.suggested_time.strftime("%b %d %Y %H:%M")
            if suggestion.suggested_time
            else "Soon"
        )
    )

    action = (suggestion.message or "No additional details provided.").strip()
    if not action.endswith((".", "!", "?")):
        action += "."

    message = textwrap.dedent(
        f"""**{category} – {suggestion.title}**

- **Action:** {action}
- **Deadline:** {deadline_text}
"""
    )

    payload = {
        "username": "Study Buddy Suggestions",
        "content": message,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception:
        return False

