# Copy this into app/main.py

# ============================================
# ADD TO IMPORTS (at top of file)
# ============================================
from datetime import datetime, timedelta
from notifications.autonomous import (
    send_discord_embed,
    send_tool_completion_notification,
    send_execution_summary,
    send_ntfy_notification,
)
from notifications.dispatcher import set_ntfy_topic

# NOTE: Make sure ToolCallTracker takes an optional flag to enable notifications

# ============================================
# ADD AFTER OTHER GLOBALS
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
# ADD PYDANTIC MODELS (with other models)
# ============================================
class AutonomousConfigPayload(BaseModel):
    enabled: bool
    frequency: Literal["15min", "30min", "1hour", "3hours", "6hours", "12hours", "24hours"]
    discord_webhook: Optional[str] = None
    ntfy_topic: Optional[str] = None

class AutonomousConfigResponse(AutonomousConfigPayload):
    last_execution: Optional[str] = None
    next_execution: Optional[str] = None

class TestWebhookPayload(BaseModel):
    webhook_url: str

# ============================================
# ADD GLOBAL CONFIG (after other globals)
# ============================================
# Get default ntfy topic from environment
DEFAULT_NTFY_TOPIC = os.getenv("NTFY_DEFAULT_TOPIC", "gradent-ai-test-123")

AUTONOMOUS_CONFIG = {
    "enabled": False,
    "frequency": "1hour",
    "discord_webhook": None,
    "ntfy_topic": DEFAULT_NTFY_TOPIC,
    "last_execution": None,
    "next_execution": None,
}

# ============================================
# ADD ENDPOINTS (before if __name__ == "__main__")
# ============================================

# Background scheduler functions
async def autonomous_scheduler_loop():
    """Background task that runs autonomous agent on configured schedule."""
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
        send_notifications=True,  # ← Enable notifications for autonomous mode!
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


# API Endpoints

@app.get("/api/autonomous/config", response_model=AutonomousConfigResponse)
async def get_autonomous_config():
    """Get current autonomous mode configuration."""
    return AutonomousConfigResponse(**AUTONOMOUS_CONFIG)


@app.put("/api/autonomous/config", response_model=SimpleStatusResponse)
async def update_autonomous_config(payload: AutonomousConfigPayload):
    """Update autonomous mode configuration."""
    global AUTONOMOUS_CONFIG
    
    AUTONOMOUS_CONFIG["enabled"] = payload.enabled
    AUTONOMOUS_CONFIG["frequency"] = payload.frequency
    AUTONOMOUS_CONFIG["discord_webhook"] = payload.discord_webhook
    AUTONOMOUS_CONFIG["ntfy_topic"] = payload.ntfy_topic
    
    # IMPORTANT: Sync with dispatcher if you're using it
    if payload.ntfy_topic:
        set_ntfy_topic(payload.ntfy_topic)
    
    logger.info(f"Autonomous config updated: enabled={payload.enabled}, frequency={payload.frequency}, ntfy_topic={payload.ntfy_topic}")
    
    return SimpleStatusResponse(status="ok", message="Configuration updated")


@app.post("/api/autonomous/execute", response_model=SimpleStatusResponse)
async def trigger_autonomous_execution():
    """Manually trigger autonomous agent execution (independent of schedule)."""
    logger.info("Manual trigger of autonomous execution")
    
    try:
        await execute_autonomous_agent()
        
        # Update last execution time
        now = datetime.utcnow()
        AUTONOMOUS_CONFIG["last_execution"] = now.isoformat()
        frequency = AUTONOMOUS_CONFIG.get("frequency", "1hour")
        next_run = now + timedelta(minutes=FREQUENCY_TO_MINUTES.get(frequency, 60))
        AUTONOMOUS_CONFIG["next_execution"] = next_run.isoformat()
        
        return SimpleStatusResponse(status="ok", message="Execution completed")
    except Exception as e:
        logger.error(f"Manual autonomous execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/autonomous/test-webhook", response_model=SimpleStatusResponse)
async def test_discord_webhook(payload: TestWebhookPayload):
    """Send a test notification to Discord webhook."""
    success = await send_discord_embed(
        payload.webhook_url,
        "🧪 Test Notification",
        "This is a test from GradEnt AI Autonomous Mode! 🤖\n\nYour webhook is working correctly!",
        5814783  # Teal
    )
    
    if success:
        return SimpleStatusResponse(status="ok", message="Test notification sent")
    else:
        raise HTTPException(status_code=400, detail="Failed to send notification")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    # Start autonomous scheduler in background
    asyncio.create_task(autonomous_scheduler_loop())
    logger.info("✓ Autonomous scheduler task started")


