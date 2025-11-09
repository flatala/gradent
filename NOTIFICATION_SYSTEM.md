# Autonomous Mode - Notification System

## Overview
Notifications should be sent **every time** the executor agent completes a meaningful action (scheduling event, generating suggestions, assessing assignments).

## Architecture

### 1. Notification Hook in Tool Callbacks

The backend should use the same `ToolCallTracker` callback system we already have, but extend it to send Discord notifications:

```python
class AutonomousToolCallTracker(BaseCallbackHandler):
    """Callback handler that tracks tool calls AND sends Discord notifications."""
    
    def __init__(self, discord_webhook: Optional[str] = None):
        self.discord_webhook = discord_webhook
        self.tool_calls: List[Dict[str, Any]] = []
        self.tool_map = {
            "run_scheduler_workflow": {
                "type": "scheduler",
                "name": "Schedule Meeting",
                "icon": "📅",
                "color": 3447003  # Blue
            },
            "assess_assignment": {
                "type": "assessment",
                "name": "Assess Assignment",
                "icon": "📊",
                "color": 15844367  # Gold
            },
            "generate_suggestions": {
                "type": "suggestions",
                "name": "Generate Suggestions",
                "icon": "💡",
                "color": 5763719  # Green
            },
            "run_exam_api_workflow": {
                "type": "exam_generation",
                "name": "Generate Exam",
                "icon": "🧠",
                "color": 10181046  # Purple
            },
        }
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Called when a tool starts executing."""
        tool_name = serialized.get("name", "unknown")
        if tool_name in self.tool_map:
            tool_info = self.tool_map[tool_name]
            self.tool_calls.append({
                "tool_name": tool_info["name"],
                "tool_type": tool_info["type"],
                "icon": tool_info["icon"],
                "color": tool_info["color"],
                "status": "started",
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.info(f"AUTONOMOUS TOOL STARTED: {tool_name}")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool finishes - SEND NOTIFICATION HERE."""
        if self.tool_calls:
            last_tool = self.tool_calls[-1]
            if last_tool["status"] == "started":
                last_tool["status"] = "completed"
                try:
                    last_tool["result"] = json.loads(output) if output else {}
                except json.JSONDecodeError:
                    last_tool["result"] = {"message": output}
                
                logger.info(f"AUTONOMOUS TOOL COMPLETED: {last_tool['tool_name']}")
                
                # Send Discord notification
                if self.discord_webhook:
                    asyncio.create_task(
                        self._send_tool_completion_notification(last_tool)
                    )
    
    async def _send_tool_completion_notification(self, tool_call: Dict[str, Any]):
        """Send a Discord notification when a tool completes."""
        try:
            # Format the notification based on tool type
            title = f"{tool_call['icon']} {tool_call['tool_name']} Completed"
            description = self._format_tool_result(tool_call)
            
            await send_discord_notification(
                self.discord_webhook,
                title,
                description,
                color=tool_call["color"]
            )
            logger.info(f"Discord notification sent for {tool_call['tool_name']}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
    
    def _format_tool_result(self, tool_call: Dict[str, Any]) -> str:
        """Format the tool result for Discord notification."""
        result = tool_call.get("result", {})
        tool_type = tool_call["tool_type"]
        
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
```

### 2. Update run_autonomous_agent Function

```python
async def run_autonomous_agent():
    """Execute the autonomous agent workflow."""
    logger.info("Starting autonomous agent execution")
    
    # Get Discord webhook from config
    discord_webhook = AUTONOMOUS_CONFIG.get("discord_webhook")
    
    # Send "Starting" notification
    if discord_webhook:
        await send_discord_notification(
            discord_webhook,
            "🤖 Autonomous Agent Started",
            "Running scheduled tasks...\n\n⏳ Checking for updates and generating plans...",
            color=5814783  # Teal
        )
    
    try:
        # Import executor agent
        from agents.executor_agent.agent import ExecutorAgent
        
        # Create config
        config = _require_agent_config()
        
        # Create callback tracker with Discord webhook
        tracker = AutonomousToolCallTracker(discord_webhook=discord_webhook)
        
        # Initialize executor agent
        executor = ExecutorAgent(config)
        
        # Run the agent with callbacks
        result = await executor.execute(callbacks=[tracker])
        
        # Update execution times
        AUTONOMOUS_CONFIG["last_execution"] = datetime.utcnow().isoformat()
        AUTONOMOUS_CONFIG["next_execution"] = calculate_next_execution(
            AUTONOMOUS_CONFIG["frequency"]
        )
        
        # Send summary notification
        if discord_webhook:
            summary = _format_execution_summary(tracker.tool_calls)
            await send_discord_notification(
                discord_webhook,
                "✅ Autonomous Agent Completed",
                summary,
                color=3066993  # Green
            )
        
        logger.info(f"Autonomous agent execution completed")
        
    except Exception as e:
        logger.error(f"Autonomous agent execution failed: {e}")
        
        # Send error notification
        if discord_webhook:
            await send_discord_notification(
                discord_webhook,
                "❌ Autonomous Agent Error",
                f"Execution failed:\n```{str(e)}```\n\nPlease check logs for details.",
                color=15158332  # Red
            )

def _format_execution_summary(tool_calls: List[Dict[str, Any]]) -> str:
    """Format a summary of all tool calls for final notification."""
    completed = [tc for tc in tool_calls if tc["status"] == "completed"]
    failed = [tc for tc in tool_calls if tc["status"] == "failed"]
    
    summary = f"**Execution Summary**\n\n"
    summary += f"✅ Completed: {len(completed)} task{'s' if len(completed) != 1 else ''}\n"
    
    if failed:
        summary += f"❌ Failed: {len(failed)} task{'s' if len(failed) != 1 else ''}\n"
    
    summary += "\n**Tasks Performed:**\n"
    for tc in completed:
        summary += f"• {tc['icon']} {tc['tool_name']}\n"
    
    next_exec = AUTONOMOUS_CONFIG.get("next_execution", "")
    if next_exec:
        summary += f"\n⏰ Next execution: <t:{int(datetime.fromisoformat(next_exec).timestamp())}:R>"
    
    return summary
```

### 3. Discord Notification Examples

**When scheduling a meeting:**
```
📅 Schedule Meeting Completed

Meeting: Study Session - Data Structures
Time: 2024-01-15 14:00:00
Duration: 90 minutes
[View in Calendar](https://calendar.google.com/...)
```

**When generating suggestions:**
```
💡 Generate Suggestions Completed

Generated 5 new study suggestions!

1. Review Chapter 3: Binary Trees
2. Practice LeetCode problems on Graphs
3. Complete Assignment 2 by Wednesday

...and 2 more
```

**When assessing assignment:**
```
📊 Assess Assignment Completed

Assignment Assessed

📊 Effort: 8 hours
⚡ Difficulty: 4/5
⚠️ Risk Score: 65/100

Milestones: 4 identified
```

**Final summary:**
```
✅ Autonomous Agent Completed

Execution Summary

✅ Completed: 3 tasks
❌ Failed: 0 tasks

Tasks Performed:
• 📊 Assess Assignment
• 💡 Generate Suggestions
• 📅 Schedule Meeting

⏰ Next execution: in 1 hour
```

### 4. Real-time vs Batch Notifications

**Option A: Real-time (Recommended)**
- Send notification immediately when each tool completes
- User gets instant updates
- More engaging and informative

**Option B: Batch**
- Collect all results
- Send one summary notification at the end
- Less spammy but less informative

**Hybrid Approach (Best):**
- Send real-time notifications for **important** actions (scheduling, new suggestions)
- Skip notifications for minor actions (progress logging)
- Always send final summary

### 5. Notification Settings (Future Enhancement)

Add to `AutonomousConfigPayload`:
```python
class NotificationSettings(BaseModel):
    notify_on_start: bool = True
    notify_on_completion: bool = True
    notify_on_error: bool = True
    notify_per_tool: bool = True  # Send notification for each tool
    notify_summary_only: bool = False  # Only send final summary

class AutonomousConfigPayload(BaseModel):
    enabled: bool
    frequency: str
    discord_webhook: Optional[str] = None
    notification_settings: NotificationSettings = NotificationSettings()
```

## Testing the Notification Flow

1. **Setup Discord Webhook**:
   - Go to Discord Server Settings → Integrations → Webhooks
   - Create new webhook
   - Copy URL

2. **Configure in UI**:
   - Paste webhook URL in Autonomous Mode settings
   - Click "Send Test Notification"
   - Should see test message in Discord

3. **Trigger Manual Execution**:
   - Click "Run Now" button
   - Watch Discord channel for notifications:
     - "🤖 Autonomous Agent Started"
     - Individual tool notifications as they complete
     - "✅ Autonomous Agent Completed" summary

4. **Schedule Execution**:
   - Enable autonomous mode
   - Set frequency (e.g., "Every hour")
   - Wait for scheduled execution
   - Notifications will appear automatically

## Implementation Checklist

- [ ] Add `AutonomousToolCallTracker` callback handler
- [ ] Update `run_autonomous_agent()` to use callbacks
- [ ] Implement `_format_tool_result()` for each tool type
- [ ] Implement `_format_execution_summary()`
- [ ] Add notification settings (optional)
- [ ] Test with real Discord webhook
- [ ] Add error handling for webhook failures
- [ ] Consider rate limiting (Discord has limits)

## Benefits

✅ **Transparency**: User knows exactly what the agent is doing
✅ **Engagement**: Get notified on Discord/mobile when tasks complete
✅ **Debugging**: Easier to see what's working/failing
✅ **Trust**: Clear visibility into autonomous actions

This way, every meaningful action (schedule, suggestion, assessment) triggers its own notification, keeping you informed in real-time! 🔔

