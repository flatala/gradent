# 🔔 Notification System - Quick Reference

## When Notifications Are Sent

### ❌ NEVER Send Notifications
- **Chat Mode** - User talking to AI assistant
- Regular `/api/chat` endpoint
- `ToolCallTracker()`  ← Default, send_notifications=False
- **Why:** Don't spam users during normal conversation

### ✅ ALWAYS Send Notifications  
- **Autonomous Mode** - Background agent execution
- `/api/autonomous/execute` endpoint
- `ToolCallTracker(send_notifications=True, ...)`
- **Why:** User isn't actively watching, needs alerts

## Usage Examples

### Chat Endpoint (Existing - Don't Change)
```python
# app/main.py - /api/chat endpoint
@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    # Create tracker WITHOUT notifications (default)
    tracker = ToolCallTracker()  # ← send_notifications=False by default
    
    agent = get_or_create_agent(payload.session_id)
    response = await agent.chat(payload.message, callbacks=[tracker])
    
    # ✅ Tools tracked in UI
    # ❌ No notifications sent
    return ChatResponse(message=response, tool_calls=tracker.tool_calls)
```

### Autonomous Endpoint (Add This)
```python
# app/main.py - /api/autonomous/execute endpoint
@app.post("/api/autonomous/execute")
async def trigger_autonomous_execution():
    # Get config
    ntfy_topic = AUTONOMOUS_CONFIG.get("ntfy_topic")
    discord_webhook = AUTONOMOUS_CONFIG.get("discord_webhook")
    
    # Create tracker WITH notifications
    tracker = ToolCallTracker(
        send_notifications=True,  # ← Enable notifications!
        discord_webhook=discord_webhook,
        ntfy_topic=ntfy_topic
    )
    
    # Run executor agent
    # executor = ExecutorAgent(config=AGENT_CONFIG)
    # executor.run(callbacks=[tracker])
    
    # ✅ Tools tracked in UI
    # ✅ Notifications sent to Discord/ntfy
    return {"status": "ok"}
```

## Notification Channels

Configure in Autonomous Mode UI:

| Channel | Configuration | When Sent |
|---------|---------------|-----------|
| ntfy | `ntfy_topic: "my-topic"` | If topic is set |
| Discord | `discord_webhook: "https://..."` | If webhook is set |
| Both | Both values set | **Both channels get notifications!** |
| Neither | Both empty/null | No notifications (only UI tracking) |

## Key Points

1. **Chat = No Notifications** (ever)
2. **Autonomous = Notifications** (if configured)
3. **Can use both Discord AND ntfy** (recommended for redundancy)
4. **Default is safe** (send_notifications=False won't spam)

## Logging

Watch the logs to see what's happening:

```bash
# Chat mode
INFO: TOOL COMPLETED: Generate Suggestions
DEBUG: [CHAT MODE] No notifications sent for tool: Generate Suggestions

# Autonomous mode  
INFO: TOOL COMPLETED: Generate Suggestions
INFO: [AUTONOMOUS MODE] Sending notifications for tool: Generate Suggestions
```

## Testing Checklist

- [ ] Chat with AI → No notifications received ✅
- [ ] Configure ntfy topic in Autonomous Mode
- [ ] Click "Run Now" → Notifications received ✅
- [ ] Configure Discord webhook
- [ ] Click "Run Now" → Both Discord and ntfy get notifications ✅

## Environment Variables

```bash
# Default ntfy topic (can be overridden in UI)
NTFY_DEFAULT_TOPIC=gradent-ai-test-123

# Optional Discord webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

**Remember:** Autonomous mode ONLY! Chat stays quiet. 🔕→💬  📢→🤖

