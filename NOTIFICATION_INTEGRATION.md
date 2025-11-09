# 🔗 Notification System Integration Guide

## What Changed

### ✅ Updated Files

1. **`notifications/dispatcher.py`** - Now supports ntfy notifications
2. **`notifications/discord.py`** - Added async version with ntfy support
3. **`notifications/autonomous.py`** - Already had ntfy support (unchanged)

## How It All Works Together

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│                     (app/main.py)                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. User configures:                                     │
│     - discord_webhook: "https://discord.com/api/..."    │
│     - ntfy_topic: "gradent-ai"                          │
│                                                          │
│  2. Three notification paths:                            │
│     ┌──────────────────────────────────────────────┐   │
│     │ A. Tool Call Notifications                    │   │
│     │    (autonomous.py)                            │   │
│     │    - When agent runs tools                    │   │
│     │    - Sends to Discord + ntfy                  │   │
│     └──────────────────────────────────────────────┘   │
│                                                          │
│     ┌──────────────────────────────────────────────┐   │
│     │ B. Suggestion Dispatcher                      │   │
│     │    (dispatcher.py)                            │   │
│     │    - Polls database for due suggestions       │   │
│     │    - Sends to Discord + ntfy                  │   │
│     └──────────────────────────────────────────────┘   │
│                                                          │
│     ┌──────────────────────────────────────────────┐   │
│     │ C. Direct Discord Notifications               │   │
│     │    (discord.py)                               │   │
│     │    - Legacy system, backward compatible       │   │
│     │    - Can optionally include ntfy             │   │
│     └──────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Integration in `app/main.py`

### Step 1: Add Global Config

```python
from notifications.dispatcher import set_ntfy_topic

# Autonomous mode configuration
AUTONOMOUS_CONFIG = {
    "enabled": False,
    "frequency": "1hour",
    "discord_webhook": None,
    "ntfy_topic": "gradent-ai",
    "last_execution": None,
    "next_execution": None,
}
```

### Step 2: Update Config Endpoint to Sync Dispatcher

```python
@app.put("/api/autonomous/config", response_model=SimpleStatusResponse)
async def update_autonomous_config(payload: AutonomousConfigPayload):
    """Update autonomous mode configuration."""
    global AUTONOMOUS_CONFIG
    
    AUTONOMOUS_CONFIG["enabled"] = payload.enabled
    AUTONOMOUS_CONFIG["frequency"] = payload.frequency
    AUTONOMOUS_CONFIG["discord_webhook"] = payload.discord_webhook
    AUTONOMOUS_CONFIG["ntfy_topic"] = payload.ntfy_topic
    
    # IMPORTANT: Also update the dispatcher's ntfy topic
    if payload.ntfy_topic:
        set_ntfy_topic(payload.ntfy_topic)
    
    return SimpleStatusResponse(status="ok", message="Configuration updated")
```

### Step 3: Initialize Dispatcher on Startup

```python
from notifications.dispatcher import set_ntfy_topic, run_scheduler

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Set ntfy topic from config
    if AUTONOMOUS_CONFIG.get("ntfy_topic"):
        set_ntfy_topic(AUTONOMOUS_CONFIG["ntfy_topic"])
    
    # Optionally start the dispatcher in the background
    # asyncio.create_task(run_scheduler())
```

### Step 4: Tool Call Notifications (Already in your callback)

```python
class AutonomousToolCallTracker(BaseCallbackHandler):
    def __init__(self, discord_webhook: Optional[str] = None, ntfy_topic: Optional[str] = None):
        self.discord_webhook = discord_webhook
        self.ntfy_topic = ntfy_topic
        self.tool_calls = []
        self.current_tool = None
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        if self.current_tool:
            last_tool = self.tool_calls[-1]
            last_tool["status"] = "completed"
            
            # Send notifications to both Discord and ntfy!
            asyncio.create_task(
                send_tool_completion_notification(
                    self.discord_webhook or "",
                    last_tool["tool_type"],
                    last_tool["tool_name"],
                    last_tool["result"],
                    ntfy_topic=self.ntfy_topic  # Pass ntfy topic
                )
            )
```

## Using the Dispatcher

### Option A: Run as Standalone Service

The dispatcher can run independently to monitor the database and send notifications:

```bash
# Run dispatcher as a background service
cd /Users/alex.zheng/hackathon/gradent
python -m notifications.dispatcher
```

This will:
- Poll the database every 10 seconds (configurable)
- Find suggestions that are due
- Send notifications to Discord (if configured)
- Send notifications to ntfy (if topic is set)

### Option B: Embed in FastAPI

You can also start the dispatcher as part of your FastAPI app:

```python
from notifications.dispatcher import run_scheduler, set_ntfy_topic

@app.on_event("startup")
async def startup_event():
    """Start background tasks."""
    # Set ntfy topic
    if AUTONOMOUS_CONFIG.get("ntfy_topic"):
        set_ntfy_topic(AUTONOMOUS_CONFIG["ntfy_topic"])
    
    # Start dispatcher in background
    asyncio.create_task(run_scheduler())
    
    logger.info("Suggestion dispatcher started")
```

## Notification Flow Examples

### Example 1: Agent Completes a Tool

```
User clicks "Run Now" in Autonomous Mode
    ↓
Agent executes run_scheduler_workflow tool
    ↓
ToolCallTracker detects completion
    ↓
Calls send_tool_completion_notification()
    ↓
Sends to:
    - Discord (rich embed)
    - ntfy (push notification)
    ↓
User gets notifications on:
    ✅ Discord desktop app
    ✅ Phone (ntfy app)
    ✅ Browser (ntfy.sh web)
    ✅ Email (if configured)
```

### Example 2: Suggestion Becomes Due

```
Suggestion in database with suggested_time = NOW
    ↓
Dispatcher polls database
    ↓
Finds due suggestion
    ↓
Calls send_discord_notification()
    ↓
ALSO calls send_ntfy_notification()
    ↓
Updates suggestion status to NOTIFIED
    ↓
User gets notification about what to study
```

### Example 3: Manual Test

```
User enters Discord webhook in UI
    ↓
Clicks "Send Test Notification"
    ↓
Backend calls send_discord_embed()
    ↓
Discord webhook receives test message
    ↓
User confirms webhook works
```

## Configuration Priority

All three systems respect this priority:

1. **Function parameter** (if provided directly)
2. **Environment variable** (`DISCORD_WEBHOOK_URL`)
3. **Global config** (`AUTONOMOUS_CONFIG`)
4. **Dispatcher global** (`_ntfy_topic`)

## Testing Each Component

### Test 1: Direct ntfy Function

```python
from notifications.autonomous import send_ntfy_notification
import asyncio

asyncio.run(send_ntfy_notification(
    "Test message",
    topic="gradent-ai-test",
    title="Test",
    priority=5
))
```

### Test 2: Dispatcher with ntfy

```python
from notifications.dispatcher import set_ntfy_topic, dispatch_once

# Set topic
set_ntfy_topic("gradent-ai-test")

# Manually trigger one dispatch cycle
sent = dispatch_once()
print(f"Sent {sent} notifications")
```

### Test 3: Full Integration via API

```bash
# 1. Configure
curl -X PUT http://localhost:8000/api/autonomous/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "frequency": "1hour",
    "ntfy_topic": "my-study-ai"
  }'

# 2. Subscribe
# Open https://ntfy.sh/my-study-ai in browser

# 3. Trigger execution
curl -X POST http://localhost:8000/api/autonomous/execute

# 4. Get notification!
```

## Benefits of This Architecture

✅ **Redundancy** - If Discord is down, ntfy still works
✅ **Multi-channel** - Users get notifications where they want
✅ **Backward compatible** - Old Discord-only code still works
✅ **Easy to extend** - Add Slack, Telegram, etc. by following same pattern
✅ **Independent** - Dispatcher can run separately from main app
✅ **Testable** - Each component can be tested independently

## Environment Variables

The system respects these environment variables:

```bash
# Discord (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Dispatcher settings
SUGGESTION_POLL_SECONDS=10
SUGGESTION_MAX_PER_CYCLE=1

# ntfy topic (can be set via UI instead)
NTFY_TOPIC=gradent-ai
```

## Next Steps

1. ✅ Add the autonomous config endpoints to `app/main.py`
2. ✅ Add `set_ntfy_topic()` call when config is updated
3. ✅ Pass `ntfy_topic` to your `ToolCallTracker`
4. 🔄 Optionally: Start dispatcher on app startup
5. 🔄 Test the full flow with real notifications

All the notification code is ready - just wire up the endpoints!

