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
        headers = {}
        if title:
            headers["Title"] = title
        if tags:
            headers["Tags"] = ",".join(tags)
        headers["Priority"] = str(priority)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://ntfy.sh/{topic}",
                data=message.encode('utf-8'),
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"ntfy notification sent to {topic}: {title or message[:50]}")
            return True
    except Exception as e:
        logger.error(f"Failed to send ntfy notification: {e}")
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
        tool_type: Type of tool (scheduler, assessment, suggestions, exam_generation)
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
    """Format tool result for Discord notification."""
    
    if tool_type == "scheduler":
        # Scheduling notification
        meeting_name = result.get("meeting_name", "Study Session")
        start_time = result.get("start_time", "")
        duration = result.get("duration_minutes", "")

        description = f"**Meeting**: {meeting_name}\n"
        if start_time:
            description += f"**Time**: {start_time}\n"
        if duration:
            description += f"**Duration**: {duration} minutes\n"
        if result.get("event_link"):
            description += f"[View in Calendar]({result['event_link']})"

        return description

    elif tool_type == "suggestions":
        # Suggestions notification
        suggestions = result.get("suggestions", [])
        count = len(suggestions)

        description = f"Generated **{count}** new study suggestion{'s' if count != 1 else ''}!\n\n"

        # Show first 3 suggestions
        for i, sugg in enumerate(suggestions[:3]):
            title = sugg.get("title", "")
            description += f"{i+1}. {title}\n"

        if count > 3:
            description += f"\n_...and {count - 3} more_"

        return description

    elif tool_type == "assessment":
        # Assessment notification
        effort = result.get("effort_estimates", {})
        hours = effort.get("most_likely_hours", effort.get("effort_hours_most", "N/A"))
        difficulty = result.get("difficulty_1to5", "N/A")
        risk = result.get("risk_score_0to100", "N/A")

        description = f"**Assignment Assessed**\n\n"
        description += f"📊 **Effort**: {hours} hours\n"
        description += f"⚡ **Difficulty**: {difficulty}/5\n"
        description += f"⚠️ **Risk Score**: {risk}/100\n"

        milestones = result.get("milestones", [])
        if milestones:
            description += f"\n**Milestones**: {len(milestones)} identified"

        return description

    elif tool_type == "exam_generation":
        # Exam generation notification
        questions_count = result.get("questions_count", result.get("total_questions", "N/A"))

        description = f"**Exam Generated**\n\n"
        description += f"📝 **Questions**: {questions_count}\n"

        if result.get("exam_file"):
            description += f"[Download Exam]({result['exam_file']})"

        return description

    return "Task completed successfully! ✅"


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

