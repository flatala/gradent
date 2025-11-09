"""Enhanced Discord notification system for autonomous mode."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)


async def send_discord_embed(
    webhook_url: str,
    title: str,
    description: str,
    color: int = 5814783,
    fields: Optional[list[Dict[str, Any]]] = None,
) -> bool:
    """Send an embed message to Discord webhook (async version).

    Args:
        webhook_url: Discord webhook URL
        title: Embed title
        description: Embed description
        color: Embed color (decimal)
        fields: Optional list of fields [{"name": "...", "value": "...", "inline": False}]

    Returns:
        bool indicating success
    """
    if not webhook_url:
        logger.warning("No Discord webhook URL provided")
        return False

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "GradEnt AI Autonomous Mode"},
    }

    if fields:
        embed["fields"] = fields

    payload = {"embeds": [embed]}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Discord notification sent: {title}")
            return True
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")
        return False


async def send_ntfy_notification(
    message: str,
    topic: str = "gradent-ai",
    title: Optional[str] = None,
    priority: int = 3,
    tags: Optional[list[str]] = None,
) -> bool:
    """Send notification to ntfy.sh - anyone can subscribe!
    
    Args:
        message: Notification message
        topic: ntfy topic (default: gradent-ai)
        title: Optional notification title
        priority: 1=min, 3=default, 5=max
        tags: Optional list of emoji tags like ["tada", "robot"]
    
    Returns:
        bool indicating success
    """
    if not topic:
        return False
        
    try:
        # Use JSON format for better Unicode/emoji support
        payload = {
            "topic": topic,
            "message": message,
            "priority": priority,
        }
        
        if title:
            payload["title"] = title
        
        if tags:
            payload["tags"] = tags
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://ntfy.sh",
                json=payload,  # JSON automatically handles UTF-8
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"ntfy notification sent to {topic}: {title or message[:50]}")
            return True
    except Exception as e:
        logger.error(f"Failed to send ntfy notification: {e}", exc_info=True)
        return False


async def send_tool_completion_notification(
    webhook_url: str,
    tool_type: str,
    tool_name: str,
    result: Dict[str, Any],
    ntfy_topic: Optional[str] = None,
) -> bool:
    """Send a notification when a tool completes.
    Now supports both Discord and ntfy!

    Args:
        webhook_url: Discord webhook URL
        tool_type: Type of tool (scheduler, assessment, suggestions, exam_generation, context_update, query)
        tool_name: Human-readable name
        result: Tool result data
        ntfy_topic: Optional ntfy topic (if provided, also sends to ntfy)

    Returns:
        bool indicating success
    """
    # Icon and color mapping
    tool_config = {
        "scheduler": {"icon": "📅", "color": 3447003, "emoji": "calendar"},  # Blue
        "assessment": {"icon": "📊", "color": 15844367, "emoji": "bar_chart"},  # Gold
        "suggestions": {"icon": "💡", "color": 5763719, "emoji": "bulb"},  # Green
        "exam_generation": {"icon": "🧠", "color": 10181046, "emoji": "brain"},  # Purple
        "context_update": {"icon": "🔄", "color": 5793266, "emoji": "arrows_counterclockwise"},  # Teal
        "query": {"icon": "🔍", "color": 9807270, "emoji": "mag"},  # Gray
    }

    config = tool_config.get(tool_type, {"icon": "✅", "color": 5814783, "emoji": "white_check_mark"})
    title = f"{config['icon']} {tool_name} Completed"
    description = _format_tool_result(tool_type, result)

    # Send to Discord if webhook provided
    discord_success = True
    if webhook_url:
        discord_success = await send_discord_embed(webhook_url, title, description, config["color"])
    
    # ALSO send to ntfy if topic provided
    if ntfy_topic:
        # Format for ntfy (simpler, no markdown)
        ntfy_message = f"{tool_name} completed!\n\n{description}"
        await send_ntfy_notification(
            message=ntfy_message,
            topic=ntfy_topic,
            title=title,
            priority=4,  # High priority
            tags=[config["emoji"], "robot"]
        )
    
    return discord_success


def _format_tool_result(tool_type: str, result: Dict[str, Any]) -> str:
    """Format tool result for mobile notification - keep it SHORT!"""
    
    if tool_type == "scheduler":
        # Scheduling notification - mobile friendly
        meeting_name = result.get("meeting_name", "Study Session")
        start_time = result.get("start_time", result.get("scheduled_time", ""))
        
        # Parse and format time nicely
        if start_time:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                time_str = dt.strftime("%b %d at %I:%M %p")
            except:
                time_str = start_time
            return f"📅 {meeting_name}\n{time_str}"
        
        return f"📅 {meeting_name} scheduled!"
    
    elif tool_type == "suggestions":
        # Suggestions notification - show top priority only
        if isinstance(result, list):
            suggestions = result
        else:
            suggestions = result.get("suggestions", [])
        
        if not suggestions:
            return "No urgent suggestions right now"
        
        count = len(suggestions)
        if count == 0:
            return "No urgent suggestions right now"
        
        # Show only the first (most important) suggestion
        first = suggestions[0]
        title = first.get("title", "Study reminder")
        
        if count == 1:
            return f"💡 {title}"
        else:
            return f"💡 {title}\n+{count-1} more"
    
    return "✅ Task completed"


async def send_execution_summary(
    webhook_url: str,
    completed_count: int,
    failed_count: int,
    tool_calls: list[Dict[str, Any]],
    next_execution: Optional[str] = None,
    ntfy_topic: Optional[str] = None,
) -> bool:
    """Send a summary notification after autonomous execution.

    Args:
        webhook_url: Discord webhook URL
        completed_count: Number of completed tasks
        failed_count: Number of failed tasks
        tool_calls: List of tool call info
        next_execution: ISO format timestamp of next execution
        ntfy_topic: Optional ntfy topic (if provided, also sends to ntfy)

    Returns:
        bool indicating success
    """
    summary = f"**Execution Summary**\n\n"
    summary += f"✅ Completed: {completed_count} task{'s' if completed_count != 1 else ''}\n"

    if failed_count > 0:
        summary += f"❌ Failed: {failed_count} task{'s' if failed_count != 1 else ''}\n"

    summary += "\n**Tasks Performed:**\n"
    for tc in tool_calls:
        if tc.get("status") == "completed":
            icon = {"scheduler": "📅", "assessment": "📊", "suggestions": "💡", "exam_generation": "🧠"}.get(
                tc.get("tool_type", ""), "✅"
            )
            summary += f"• {icon} {tc.get('tool_name', 'Unknown')}\n"

    if next_execution:
        try:
            next_dt = datetime.fromisoformat(next_execution)
            timestamp = int(next_dt.timestamp())
            summary += f"\n⏰ Next execution: <t:{timestamp}:R>"
        except Exception:
            summary += f"\n⏰ Next execution: {next_execution}"

    # Send to Discord
    discord_success = True
    if webhook_url:
        discord_success = await send_discord_embed(
            webhook_url,
            "✅ Autonomous Agent Completed",
            summary,
            3066993,  # Green
        )
    
    # ALSO send to ntfy
    if ntfy_topic:
        ntfy_summary = f"Autonomous Agent Completed\n\n"
        ntfy_summary += f"✅ {completed_count} task(s) completed\n"
        if failed_count > 0:
            ntfy_summary += f"❌ {failed_count} task(s) failed\n"
        
        await send_ntfy_notification(
            message=ntfy_summary,
            topic=ntfy_topic,
            title="✅ Autonomous Agent Completed",
            priority=3,
            tags=["white_check_mark", "robot", "tada"]
        )
    
    return discord_success

