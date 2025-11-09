# Running the Dispatcher (Optional)

## What It Does
The dispatcher sends notifications for suggestions that become due at their scheduled time.

**Example:**
- Autonomous agent creates suggestion: "Review Chapter 5" at 6:00 PM
- At 6:00 PM, dispatcher sends reminder notification
- User gets notified to actually do the task

## How to Run It

### Option 1: Standalone Process (Recommended)
Run as a separate background service:

```bash
cd /Users/alex.zheng/hackathon/gradent

# Run in background
python -m notifications.dispatcher &

# Or with nohup to persist after terminal closes
nohup python -m notifications.dispatcher > dispatcher.log 2>&1 &
```

### Option 2: Embedded in FastAPI
Start dispatcher when your FastAPI app starts:

```python
# Add to app/main.py

from notifications.dispatcher import run_scheduler, set_ntfy_topic

@app.on_event("startup")
async def startup_event():
    """Start background services."""
    # Set ntfy topic from config
    if AUTONOMOUS_CONFIG.get("ntfy_topic"):
        set_ntfy_topic(AUTONOMOUS_CONFIG["ntfy_topic"])
    
    # Start dispatcher in background
    asyncio.create_task(run_scheduler())
    
    logger.info("Dispatcher started - will check for due suggestions every 10 seconds")
```

## Configuration

### Environment Variables
```bash
# How often to check (seconds)
SUGGESTION_POLL_SECONDS=10

# Max suggestions per check
SUGGESTION_MAX_PER_CYCLE=1

# Optional: Discord webhook for suggestions
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Update Config When User Changes ntfy Topic
```python
# In your /api/autonomous/config endpoint
@app.put("/api/autonomous/config")
async def update_autonomous_config(payload: AutonomousConfigPayload):
    global AUTONOMOUS_CONFIG
    
    AUTONOMOUS_CONFIG["enabled"] = payload.enabled
    AUTONOMOUS_CONFIG["frequency"] = payload.frequency
    AUTONOMOUS_CONFIG["discord_webhook"] = payload.discord_webhook
    AUTONOMOUS_CONFIG["ntfy_topic"] = payload.ntfy_topic
    
    # IMPORTANT: Also update dispatcher's ntfy topic
    if payload.ntfy_topic:
        set_ntfy_topic(payload.ntfy_topic)
    
    return {"status": "ok", "message": "Configuration updated"}
```

## How It Works With Autonomous Mode

Both can work together:

```
User clicks "Run Now" in Autonomous Mode
  ↓
Autonomous agent runs
  ↓
Creates 5 suggestions in database with scheduled times:
  - "Review Chapter 3" at 6:00 PM today
  - "Practice problems" at 8:00 PM today
  - "Study for quiz" at 10:00 AM tomorrow
  ↓
Immediate notification: "5 suggestions created!" (autonomous mode)
  ↓
Later at 6:00 PM:
  Dispatcher finds "Review Chapter 3" is due
  Sends notification: "💡 Time to: Review Chapter 3" (dispatcher)
  ↓
Later at 8:00 PM:
  Dispatcher finds "Practice problems" is due
  Sends notification: "💡 Time to: Practice problems" (dispatcher)
```

## Pros & Cons

### Running the Dispatcher

**Pros:**
- ✅ Automatic reminders at scheduled times
- ✅ Users get notified when it's time to study
- ✅ Complete "reminder system" functionality
- ✅ Shows full feature set

**Cons:**
- ❌ One more process to manage
- ❌ Requires database with scheduled suggestions
- ❌ More complex setup
- ❌ Polls database every 10 seconds (minor overhead)

### Skipping the Dispatcher

**Pros:**
- ✅ Simpler setup (just FastAPI)
- ✅ Less to debug
- ✅ Autonomous notifications still work perfectly
- ✅ Good enough for hackathon demo

**Cons:**
- ❌ No time-based reminders
- ❌ Suggestions created but never reminded
- ❌ Missing "scheduled reminder" feature

## My Hackathon Recommendation

**For demo purposes: Skip the dispatcher**

Why?
1. Autonomous mode notifications are the impressive part
2. Tool call notifications show real-time AI activity
3. Scheduled reminders are less exciting in a 5-minute demo
4. Simpler = less things that can break during demo

**Show this flow instead:**
```
Demo:
1. Configure ntfy topic
2. Subscribe on phone (show to judges)
3. Click "Run Now"
4. Phone buzzes immediately with agent activity
5. Judges see real-time notifications
6. 🎉 "That's cool!"
```

## If You Do Want Scheduled Reminders for Demo

To make it impressive:

1. **Before demo:**
   ```bash
   # Start dispatcher
   python -m notifications.dispatcher &
   
   # Create a suggestion due in 2 minutes
   # (via API or database)
   ```

2. **During demo:**
   ```
   You: "I've scheduled a study reminder for right now..."
   [Wait 5 seconds]
   Phone: *BUZZ* 💡 "Time to review Chapter 5"
   You: "See? Automatic reminders at scheduled times."
   Judges: 😮
   ```

But honestly, the autonomous mode notifications are cooler!

## Quick Decision Guide

**Skip dispatcher if:**
- Just demoing for hackathon
- Want simplest setup
- Only care about real-time agent notifications

**Use dispatcher if:**
- Building production system
- Need scheduled study reminders
- Want complete feature set
- Have 2+ minutes to show scheduler in demo

---

**TL;DR:** For hackathon, skip the dispatcher. Autonomous mode notifications are enough and more impressive!

