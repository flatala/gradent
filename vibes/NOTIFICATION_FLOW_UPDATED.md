# 🔕 Updated Notification Flow - Chat vs Autonomous Mode

## Key Change: Notifications Only in Autonomous Mode

**Problem:** Users don't want notifications every time they chat with the AI.

**Solution:** `ToolCallTracker` now has a `send_notifications` flag:
- **Chat mode:** `send_notifications=False` (default) → NO notifications
- **Autonomous mode:** `send_notifications=True` → YES notifications

## How It Works Now

### Regular Chat (NO Notifications)

```python
# In /api/chat endpoint
tracker = ToolCallTracker()  # send_notifications defaults to False
agent = get_or_create_agent(session_id)
response = await agent.chat(user_message, callbacks=[tracker])

# Tools execute, tracker records them
# BUT no notifications are sent
# User just sees tool calls in Agent Activity sidebar
```

**User Experience:**
```
User: "Generate study suggestions"
      ↓
Agent: Uses generate_suggestions tool
      ↓
Tool executes, returns suggestions
      ↓
Tracker records tool call
      ↓
Frontend shows in Agent Activity sidebar
      ↓
NO NOTIFICATIONS SENT ✅
      ↓
User sees response in chat
```

### Autonomous Mode (YES Notifications)

```python
# In /api/autonomous/execute endpoint
tracker = ToolCallTracker(
    send_notifications=True,      # ← Enable notifications
    discord_webhook=discord_webhook,
    ntfy_topic=ntfy_topic
)

# Run executor agent with tracker
executor.run(callbacks=[tracker])

# Tools execute, tracker records them
# AND sends notifications for each tool completion
```

**User Experience:**
```
User: Clicks "Run Now" button
      ↓
Agent: Runs autonomously
      ↓
Tool 1: assess_assignment completes
      ↓
📱 NOTIFICATION: "Assessment Complete"
      ↓
Tool 2: generate_suggestions completes
      ↓
📱 NOTIFICATION: "Suggestions Generated"
      ↓
Tool 3: run_scheduler_workflow completes
      ↓
📱 NOTIFICATION: "Meeting Scheduled"
      ↓
Final notification: "Agent Completed"
```

## Code Comparison

### Chat Endpoint (Existing - No Changes Needed)

```python
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatPayload):
    """Chat with the AI assistant - NO notifications."""
    
    # Create tracker WITHOUT notifications
    tracker = ToolCallTracker()  # Default: send_notifications=False
    
    agent = get_or_create_agent(payload.session_id)
    response = await agent.chat(payload.message, callbacks=[tracker])
    
    return ChatResponse(
        message=response,
        tool_calls=[
            ToolCallInfo(**tc) for tc in tracker.tool_calls
        ]
    )
```

### Autonomous Endpoint (New - With Notifications)

```python
@app.post("/api/autonomous/execute")
async def trigger_autonomous_execution():
    """Execute autonomous agent - WITH notifications."""
    
    # Get notification config
    ntfy_topic = AUTONOMOUS_CONFIG.get("ntfy_topic")
    discord_webhook = AUTONOMOUS_CONFIG.get("discord_webhook")
    
    # Send start notification
    await send_ntfy_notification(
        "🤖 Autonomous agent started!",
        topic=ntfy_topic,
        title="🤖 Agent Started",
        priority=4
    )
    
    # Create tracker WITH notifications
    tracker = ToolCallTracker(
        send_notifications=True,           # ← Enable notifications!
        discord_webhook=discord_webhook,
        ntfy_topic=ntfy_topic
    )
    
    # Run executor agent
    # executor = ExecutorAgent(config=AGENT_CONFIG)
    # executor.run(callbacks=[tracker])
    # Each tool completion will trigger notifications
    
    # Send completion notification
    await send_ntfy_notification(
        "✅ Agent completed!",
        topic=ntfy_topic,
        title="✅ Completed",
        priority=3
    )
    
    return {"status": "ok"}
```

## Three Notification Paths (Updated)

### Path 1: Autonomous Tool Calls ✅
**When:** Autonomous mode is running
**Notifications:** YES (Discord AND/OR ntfy)
```
Autonomous agent runs
  → Tool completes
  → ToolCallTracker (send_notifications=True)
  → Sends notification to Discord (if webhook configured)
  → Sends notification to ntfy (if topic configured)
  → Can send to both simultaneously for redundancy!
```

**Supported configurations:**
- ✅ Only ntfy configured → Sends to ntfy
- ✅ Only Discord configured → Sends to Discord
- ✅ Both configured → Sends to BOTH channels
- ⚠️ Neither configured → No notifications (but still tracks in UI)

### Path 2: Chat Tool Calls ❌
**When:** User chats with AI
**Notifications:** NO (regardless of Discord/ntfy config)
```
User chats
  → Tool completes
  → ToolCallTracker (send_notifications=False)
  → No notifications sent to any channel
  → Only shows in UI sidebar
```

### Path 3: Scheduled Suggestions ✅
**When:** Suggestions become due (background dispatcher)
**Notifications:** YES (Discord AND/OR ntfy)
```
Dispatcher polls database
  → Finds due suggestions
  → Sends to Discord (if DISCORD_WEBHOOK_URL env var set)
  → Sends to ntfy (if topic configured via set_ntfy_topic())
  → Independent of chat/autonomous mode
```

## Benefits

✅ **No Chat Spam** - Users don't get notified for every chat interaction
✅ **Autonomous Alerts** - Users get notified when autonomous agent works in background
✅ **Clean UX** - Notifications only when user isn't actively using the app
✅ **Flexible** - Same tracker class, just a flag difference
✅ **Backward Compatible** - Existing chat code doesn't need changes

## Testing

### Test Chat (No Notifications)
```bash
# Start app
poetry run uvicorn app.main:app --reload

# Chat with AI
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "message": "Generate study suggestions"
  }'

# ✅ No notifications sent
# ✅ Tool calls show in UI sidebar
# ✅ Response returned to chat
```

### Test Autonomous (With Notifications)

#### Option 1: ntfy Only
```bash
# Subscribe to topic
open https://ntfy.sh/gradent-ai-test-123

# Configure with ONLY ntfy
curl -X PUT http://localhost:8000/api/autonomous/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "frequency": "1hour",
    "ntfy_topic": "gradent-ai-test-123"
  }'

# Trigger execution
curl -X POST http://localhost:8000/api/autonomous/execute

# ✅ Notifications sent to ntfy only
# ✅ See in browser/phone
# ✅ One notification per tool completion
```

#### Option 2: Discord Only
```bash
# Configure with ONLY Discord
curl -X PUT http://localhost:8000/api/autonomous/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "frequency": "1hour",
    "discord_webhook": "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
  }'

# Trigger execution
curl -X POST http://localhost:8000/api/autonomous/execute

# ✅ Notifications sent to Discord only
# ✅ Rich embeds with colors and details
```

#### Option 3: Both Discord AND ntfy (Recommended!)
```bash
# Subscribe to ntfy
open https://ntfy.sh/my-gradent-ai

# Configure BOTH channels
curl -X PUT http://localhost:8000/api/autonomous/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "frequency": "1hour",
    "ntfy_topic": "my-gradent-ai",
    "discord_webhook": "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
  }'

# Trigger execution
curl -X POST http://localhost:8000/api/autonomous/execute

# ✅ Notifications sent to BOTH channels!
# ✅ Discord: Rich embeds
# ✅ ntfy: Push notifications
# ✅ Redundancy: If one fails, the other still works
```

## Notification Examples by Configuration

### Configuration 1: Only ntfy
```json
{
  "ntfy_topic": "alex-studyai-123",
  "discord_webhook": null
}
```

**Result when autonomous agent runs:**
```
📱 ntfy notification 1:
   🤖 Agent Started
   Checking assignments...

📱 ntfy notification 2:
   📊 Assessment Complete
   Found 2 assignments due this week

📱 ntfy notification 3:
   💡 Suggestions Generated
   5 new study suggestions created

📱 ntfy notification 4:
   ✅ Agent Completed
   3 tasks completed successfully
```

### Configuration 2: Only Discord
```json
{
  "ntfy_topic": null,
  "discord_webhook": "https://discord.com/api/webhooks/..."
}
```

**Result when autonomous agent runs:**
```
💬 Discord message 1:
   ┌────────────────────────────────┐
   │ 🤖 Agent Started               │
   │ Checking assignments...        │
   └────────────────────────────────┘

💬 Discord message 2:
   ┌────────────────────────────────┐
   │ 📊 Assessment Complete         │
   │                                │
   │ Assignments found: 2           │
   │ Due this week: Math, Physics   │
   └────────────────────────────────┘

💬 Discord message 3:
   ┌────────────────────────────────┐
   │ 💡 Suggestions Generated       │
   │                                │
   │ • Review Chapter 3             │
   │ • Practice problems set 5      │
   │ • Study for quiz               │
   └────────────────────────────────┘
```

### Configuration 3: Both Discord AND ntfy
```json
{
  "ntfy_topic": "alex-studyai-123",
  "discord_webhook": "https://discord.com/api/webhooks/..."
}
```

**Result when autonomous agent runs:**
```
BOTH channels get notifications simultaneously!

📱 Phone (ntfy app):
   🤖 Agent Started
   📊 Assessment Complete
   💡 Suggestions Generated
   ✅ Agent Completed

💬 Discord server:
   [Rich embeds with full details]
   🤖 Agent Started
   📊 Assessment Complete (with assignment details)
   💡 Suggestions Generated (with suggestion list)
   ✅ Agent Completed (with summary)
```

**Why use both?**
- ✅ **Redundancy**: If Discord is down, ntfy still works
- ✅ **Different contexts**: Discord for team, ntfy for personal
- ✅ **Reach**: Some people prefer mobile push, others prefer Discord
- ✅ **Reliability**: Dual-channel delivery ensures message gets through

## Summary

**Before:** All tool calls would send notifications (annoying during chat)
**After:** Only autonomous mode sends notifications (perfect UX)

The key is one simple flag: `send_notifications=True/False`

- **Chat mode:** Track tools, show in UI, NO notifications to any channel
- **Autonomous mode:** Track tools, show in UI, AND send notifications to configured channels

### Notification Channel Support

| Scenario | ntfy | Discord | Result |
|----------|------|---------|--------|
| Chat mode | ❌ | ❌ | No notifications |
| Autonomous + ntfy only | ✅ | ❌ | ntfy notifications |
| Autonomous + Discord only | ❌ | ✅ | Discord notifications |
| Autonomous + both | ✅ | ✅ | **Both channels simultaneously!** |

**Recommended setup:** Configure both Discord and ntfy for maximum reliability and reach!

Best of both worlds! 🎉

