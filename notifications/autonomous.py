"""Autonomous agent notification system.

Sends notifications via ntfy.sh for mobile push notifications.
"""
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


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
    webhook_url: str,  # Kept for compatibility but unused
    tool_type: str,
    tool_name: str,
    result: Dict[str, Any],
    ntfy_topic: Optional[str] = None,
) -> bool:
    """Send a notification when a tool completes (ntfy only).

    Args:
        webhook_url: Ignored (kept for compatibility)
        tool_type: Type of tool (scheduler, suggestions)
        tool_name: Human-readable name
        result: Tool result data
        ntfy_topic: ntfy topic for push notifications

    Returns:
        bool indicating success
    """
    logger.info(f"[NOTIF] Tool completion: type={tool_type}, ntfy={'yes' if ntfy_topic else 'no'}")
    
    # Simplified titles - just the action, no "Completed"
    tool_config = {
        "scheduler": {"title": "Scheduled Meeting", "emoji": "calendar"},
        "suggestions": {"title": "Study Suggestion", "emoji": "bulb"},
    }

    config = tool_config.get(tool_type)
    if not config:
        # Skip notifications for other tool types
        logger.debug(f"[NOTIF] Skipping notification for tool type: {tool_type}")
        return True
    
    description = _format_tool_result(tool_type, result)
    
    logger.info(f"[NOTIF] Sending: {config['title']}")

    # Send to ntfy if topic provided
    if ntfy_topic:
        logger.info(f"[NOTIF] Attempting ntfy send...")
        await send_ntfy_notification(
            message=description,
            topic=ntfy_topic,
            title=config['title'],
            priority=4,  # High priority
            tags=[config["emoji"]]
        )
        return True
    
    return False


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
