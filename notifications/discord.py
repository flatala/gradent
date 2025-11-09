"""Discord notification helpers."""
from __future__ import annotations

import asyncio
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


async def send_discord_notification_async(
    suggestion: Suggestion,
    webhook_url: Optional[str] = None,
    ntfy_topic: Optional[str] = None,
) -> bool:
    """Async version that can also send to ntfy.
    
    Args:
        suggestion: database Suggestion row
        webhook_url: optional Discord webhook URL
        ntfy_topic: optional ntfy topic (if provided, also sends to ntfy)
    
    Returns:
        bool indicating success (True if either Discord or ntfy succeeded)
    """
    discord_success = send_discord_notification(suggestion, webhook_url)
    
    # Also send to ntfy if topic provided
    if ntfy_topic:
        try:
            from notifications.autonomous import send_ntfy_notification
            
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
            
            ntfy_success = await send_ntfy_notification(
                message=message,
                topic=ntfy_topic,
                title=f"💡 {category}: {suggestion.title}",
                priority=4,
                tags=["bulb", "calendar"]
            )
            
            return discord_success or ntfy_success
        except Exception as e:
            print(f"ntfy notification failed: {e}")
            return discord_success
    
    return discord_success


