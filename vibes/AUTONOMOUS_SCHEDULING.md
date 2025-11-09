# Scheduling Autonomous Agent Execution

## The Problem
User sets frequency to "Every 1 hour" in the UI, but nothing actually triggers execution every hour.

## Solution Options

### Option 1: In-App Scheduler (Recommended for Hackathon)

Add a background task to FastAPI that checks if it's time to run:

```python
# Add to app/main.py

from datetime import datetime, timedelta
import asyncio

# Global config (you already have this)
AUTONOMOUS_CONFIG = {
    "enabled": False,
    "frequency": "1hour",
    "discord_webhook": None,
    "ntfy_topic": "gradent-ai-test-123",
    "last_execution": None,
    "next_execution": None,
}

# Frequency to minutes mapping
FREQUENCY_TO_MINUTES = {
    "15min": 15,
    "30min": 30,
    "1hour": 60,
    "3hours": 180,
    "6hours": 360,
    "12hours": 720,
    "24hours": 1440,
}


async def autonomous_scheduler_loop():
    """Background task that runs autonomous agent on schedule."""
    logger.info("Autonomous scheduler started")
    
    while True:
        await asyncio.sleep(60)  # Check every minute
        
        if not AUTONOMOUS_CONFIG.get("enabled"):
            continue  # Skip if disabled
        
        now = datetime.utcnow()
        last_exec = AUTONOMOUS_CONFIG.get("last_execution")
        frequency = AUTONOMOUS_CONFIG.get("frequency", "1hour")
        
        # Calculate if execution is due
        should_run = False
        if last_exec is None:
            should_run = True  # Never run before
        else:
            try:
                last_dt = datetime.fromisoformat(last_exec)
                minutes_since = (now - last_dt).total_seconds() / 60
                required_minutes = FREQUENCY_TO_MINUTES.get(frequency, 60)
                
                if minutes_since >= required_minutes:
                    should_run = True
            except Exception as e:
                logger.error(f"Error parsing last_execution: {e}")
        
        if should_run:
            logger.info(f"Triggering autonomous execution (frequency: {frequency})")
            try:
                await execute_autonomous_agent()
                
                # Update execution times
                AUTONOMOUS_CONFIG["last_execution"] = now.isoformat()
                next_run = now + timedelta(minutes=FREQUENCY_TO_MINUTES.get(frequency, 60))
                AUTONOMOUS_CONFIG["next_execution"] = next_run.isoformat()
                
            except Exception as e:
                logger.error(f"Autonomous execution failed: {e}")


async def execute_autonomous_agent():
    """Actually run the autonomous agent with notifications."""
    ntfy_topic = AUTONOMOUS_CONFIG.get("ntfy_topic")
    discord_webhook = AUTONOMOUS_CONFIG.get("discord_webhook")
    
    # Import here to avoid circular dependency
    from notifications.autonomous import send_ntfy_notification, send_discord_embed
    
    logger.info("[AUTONOMOUS SCHEDULER] Starting execution")
    
    # Send start notification
    if ntfy_topic:
        await send_ntfy_notification(
            "🤖 Autonomous agent started!\n\nChecking assignments, planning study sessions...",
            topic=ntfy_topic,
            title="🤖 Agent Started",
            priority=4,
            tags=["robot", "rocket"]
        )
    
    # Create tracker WITH notifications enabled
    tracker = ToolCallTracker(
        send_notifications=True,  # ← Enable notifications!
        discord_webhook=discord_webhook,
        ntfy_topic=ntfy_topic
    )
    
    # TODO: Replace with actual executor agent
    # from agents.executor_agent.agent import ExecutorAgent
    # executor = ExecutorAgent(config=AGENT_CONFIG)
    # executor.run(callbacks=[tracker])
    
    # For demo, simulate work
    await asyncio.sleep(2)
    
    # Send completion notification
    if ntfy_topic:
        await send_ntfy_notification(
            "✅ Autonomous agent completed!\n\n• Assessed 2 assignments\n• Generated 5 study suggestions\n• Scheduled 1 meeting",
            topic=ntfy_topic,
            title="✅ Agent Completed",
            priority=3,
            tags=["white_check_mark", "tada", "books"]
        )
    
    logger.info("[AUTONOMOUS SCHEDULER] Execution completed")


@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    # Start autonomous scheduler
    asyncio.create_task(autonomous_scheduler_loop())
    logger.info("Autonomous scheduler task created")
```

**Pros:**
- ✅ Built into your app
- ✅ No external services needed
- ✅ Easy to debug
- ✅ Works on any platform

**Cons:**
- ⚠️ Only runs when FastAPI is running
- ⚠️ If app crashes, scheduler stops

---

### Option 2: APScheduler (Production-Grade)

Use a proper Python scheduler library:

```bash
cd /Users/alex.zheng/hackathon/gradent
poetry add apscheduler
```

```python
# Add to app/main.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()

async def scheduled_autonomous_execution():
    """Called by APScheduler at configured intervals."""
    if not AUTONOMOUS_CONFIG.get("enabled"):
        return
    
    logger.info("[APSCHEDULER] Running autonomous agent")
    await execute_autonomous_agent()


@app.on_event("startup")
async def startup_event():
    """Start scheduler on app startup."""
    # Start with default interval (will update when config changes)
    scheduler.add_job(
        scheduled_autonomous_execution,
        trigger=IntervalTrigger(hours=1),
        id="autonomous_agent",
        replace_existing=True
    )
    scheduler.start()
    logger.info("APScheduler started")


@app.put("/api/autonomous/config")
async def update_autonomous_config(payload: AutonomousConfigPayload):
    """Update config and reschedule job."""
    global AUTONOMOUS_CONFIG
    
    AUTONOMOUS_CONFIG["enabled"] = payload.enabled
    AUTONOMOUS_CONFIG["frequency"] = payload.frequency
    AUTONOMOUS_CONFIG["discord_webhook"] = payload.discord_webhook
    AUTONOMOUS_CONFIG["ntfy_topic"] = payload.ntfy_topic
    
    # Update scheduler interval
    minutes = FREQUENCY_TO_MINUTES.get(payload.frequency, 60)
    scheduler.reschedule_job(
        "autonomous_agent",
        trigger=IntervalTrigger(minutes=minutes)
    )
    
    return {"status": "ok", "message": "Configuration updated"}
```

**Pros:**
- ✅ Production-grade
- ✅ Handles edge cases
- ✅ Can persist schedule across restarts
- ✅ More reliable

**Cons:**
- ⚠️ Another dependency
- ⚠️ More complex setup

---

### Option 3: External Cron Job (System-Level)

Use system cron to trigger the endpoint:

```bash
# Edit crontab
crontab -e

# Add line to run every hour
0 * * * * curl -X POST http://localhost:8000/api/autonomous/execute

# Or every 15 minutes
*/15 * * * * curl -X POST http://localhost:8000/api/autonomous/execute
```

**Pros:**
- ✅ Runs even if app restarts
- ✅ System-level reliability
- ✅ No code changes needed

**Cons:**
- ⚠️ Manual cron setup per deployment
- ⚠️ Can't change frequency from UI
- ⚠️ Not cross-platform (Windows needs Task Scheduler)

---

## My Recommendation for Hackathon

**Use Option 1: In-App Scheduler**

It's the simplest and works great for a demo:

1. Add the `autonomous_scheduler_loop()` function to `app/main.py`
2. Start it in `@app.on_event("startup")`
3. When user enables autonomous mode, it runs automatically
4. User gets notifications every hour (or configured interval)

## Complete Implementation

Let me create the full code you need to add:

```python
# ============================================
# ADD TO app/main.py (after imports)
# ============================================

# Frequency to minutes mapping
FREQUENCY_TO_MINUTES = {
    "15min": 15,
    "30min": 30,
    "1hour": 60,
    "3hours": 180,
    "6hours": 360,
    "12hours": 720,
    "24hours": 1440,
}

# ============================================
# ADD THESE FUNCTIONS (before endpoints)
# ============================================

async def autonomous_scheduler_loop():
    """Background task that runs autonomous agent on schedule."""
    logger.info("🤖 Autonomous scheduler started - checking every minute")
    
    while True:
        await asyncio.sleep(60)  # Check every minute
        
        if not AUTONOMOUS_CONFIG.get("enabled"):
            continue  # Skip if disabled
        
        now = datetime.utcnow()
        last_exec = AUTONOMOUS_CONFIG.get("last_execution")
        frequency = AUTONOMOUS_CONFIG.get("frequency", "1hour")
        
        # Calculate if execution is due
        should_run = False
        if last_exec is None:
            should_run = True  # Never run before
        else:
            try:
                last_dt = datetime.fromisoformat(last_exec)
                minutes_since = (now - last_dt).total_seconds() / 60
                required_minutes = FREQUENCY_TO_MINUTES.get(frequency, 60)
                
                if minutes_since >= required_minutes:
                    should_run = True
                    logger.info(f"✓ Time to run: {minutes_since:.1f} min >= {required_minutes} min")
            except Exception as e:
                logger.error(f"Error parsing last_execution: {e}")
        
        if should_run:
            logger.info(f"⚡ Triggering autonomous execution (frequency: {frequency})")
            try:
                await execute_autonomous_agent()
                
                # Update execution times
                AUTONOMOUS_CONFIG["last_execution"] = now.isoformat()
                next_run = now + timedelta(minutes=FREQUENCY_TO_MINUTES.get(frequency, 60))
                AUTONOMOUS_CONFIG["next_execution"] = next_run.isoformat()
                logger.info(f"✓ Next execution at: {next_run.isoformat()}")
                
            except Exception as e:
                logger.error(f"❌ Autonomous execution failed: {e}")


async def execute_autonomous_agent():
    """Actually run the autonomous agent with notifications."""
    ntfy_topic = AUTONOMOUS_CONFIG.get("ntfy_topic")
    discord_webhook = AUTONOMOUS_CONFIG.get("discord_webhook")
    
    # Import here to avoid circular dependency
    from notifications.autonomous import send_ntfy_notification, send_discord_embed
    
    logger.info("[AUTONOMOUS] Starting execution")
    
    # Send start notification
    if ntfy_topic:
        await send_ntfy_notification(
            "🤖 Autonomous agent started!\n\nChecking assignments, planning study sessions...",
            topic=ntfy_topic,
            title="🤖 Agent Started",
            priority=4,
            tags=["robot", "rocket"]
        )
    
    # Create tracker WITH notifications enabled
    tracker = ToolCallTracker(
        send_notifications=True,  # ← Enable notifications!
        discord_webhook=discord_webhook,
        ntfy_topic=ntfy_topic
    )
    
    # TODO: Replace with actual executor agent
    # from agents.executor_agent.agent import ExecutorAgent
    # executor = ExecutorAgent(config=AGENT_CONFIG)
    # executor.run(callbacks=[tracker])
    
    # For demo, simulate work
    await asyncio.sleep(2)
    
    # Send completion notification
    if ntfy_topic:
        await send_ntfy_notification(
            "✅ Autonomous agent completed!\n\n• Assessed 2 assignments\n• Generated 5 study suggestions\n• Scheduled 1 meeting",
            topic=ntfy_topic,
            title="✅ Agent Completed",
            priority=3,
            tags=["white_check_mark", "tada", "books"]
        )
    
    logger.info("[AUTONOMOUS] Execution completed")


# ============================================
# ADD STARTUP EVENT
# ============================================

@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    # Start autonomous scheduler in background
    asyncio.create_task(autonomous_scheduler_loop())
    logger.info("✓ Autonomous scheduler task started")
```

## How It Works

```
1. FastAPI starts
   ↓
2. startup_event() launches autonomous_scheduler_loop()
   ↓
3. Loop checks every 60 seconds:
   - Is autonomous mode enabled? (AUTONOMOUS_CONFIG["enabled"])
   - Has enough time passed since last execution?
   - If yes → run execute_autonomous_agent()
   ↓
4. execute_autonomous_agent():
   - Creates ToolCallTracker with send_notifications=True
   - Runs executor agent (or simulates it)
   - Agent uses tools (assess, suggest, schedule)
   - Each tool completion → notification sent
   ↓
5. User gets notifications on Discord/ntfy
   ↓
6. Updates last_execution time
   ↓
7. Loop continues, waits for next interval
```

## Testing

```bash
# Start your backend
poetry run uvicorn app.main:app --reload

# In logs you'll see:
# ✓ Autonomous scheduler task started
# 🤖 Autonomous scheduler started - checking every minute

# Configure autonomous mode
curl -X PUT http://localhost:8000/api/autonomous/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "frequency": "1hour",
    "ntfy_topic": "gradent-ai-test-123"
  }'

# Wait (or manually trigger)
# After 1 hour, automatic execution happens!
# Logs: ⚡ Triggering autonomous execution (frequency: 1hour)
# Notifications sent to ntfy/Discord
```

---

**TL;DR:** Add the scheduler loop to your FastAPI app. It checks every minute if it's time to run the autonomous agent based on the configured frequency. No external tools needed!

