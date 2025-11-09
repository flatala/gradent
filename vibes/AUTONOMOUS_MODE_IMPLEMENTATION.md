# Autonomous Mode Backend Implementation Guide

## Overview
Autonomous Mode allows the executor agent to run automatically without user interaction, performing tasks like scheduling, assessments, and suggestions on a regular schedule.

## Backend Changes Needed

### 1. Database Schema (if using database for config storage)

Add a new table `autonomous_config`:
```sql
CREATE TABLE autonomous_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT 1,
    enabled BOOLEAN DEFAULT FALSE,
    frequency TEXT DEFAULT '1hour',  -- 15min, 30min, 1hour, 3hours, 6hours, 12hours, 24hours
    discord_webhook TEXT,
    last_execution TIMESTAMP,
    next_execution TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Alternatively, use a simple JSON file or environment variables.

### 2. New Backend Endpoints

Add to `app/main.py`:

```python
from typing import Optional
from datetime import datetime, timedelta
import asyncio
import json
import httpx

# Pydantic Models
class AutonomousConfigPayload(BaseModel):
    enabled: bool
    frequency: Literal["15min", "30min", "1hour", "3hours", "6hours", "12hours", "24hours"]
    discord_webhook: Optional[str] = None

class AutonomousConfigResponse(AutonomousConfigPayload):
    last_execution: Optional[str] = None
    next_execution: Optional[str] = None

class TestWebhookPayload(BaseModel):
    webhook_url: str

# Global state (or use database)
AUTONOMOUS_CONFIG = {
    "enabled": False,
    "frequency": "1hour",
    "discord_webhook": None,
    "last_execution": None,
    "next_execution": None,
}

# Endpoint implementations
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
    
    # Calculate next execution time
    if payload.enabled:
        AUTONOMOUS_CONFIG["next_execution"] = calculate_next_execution(payload.frequency)
    
    # Restart scheduler if needed
    if payload.enabled:
        asyncio.create_task(start_autonomous_scheduler())
    
    return SimpleStatusResponse(status="ok", message="Configuration updated")

@app.post("/api/autonomous/execute", response_model=SimpleStatusResponse)
async def trigger_autonomous_execution():
    """Manually trigger autonomous agent execution."""
    asyncio.create_task(run_autonomous_agent())
    return SimpleStatusResponse(status="ok", message="Execution started")

@app.post("/api/autonomous/test-webhook", response_model=SimpleStatusResponse)
async def test_discord_webhook(payload: TestWebhookPayload):
    """Send a test notification to Discord webhook."""
    try:
        await send_discord_notification(
            payload.webhook_url,
            "Test Notification",
            "This is a test message from GradEnt AI Autonomous Mode! 🤖"
        )
        return SimpleStatusResponse(status="ok", message="Test notification sent")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to send notification: {str(e)}")
```

### 3. Helper Functions

```python
def calculate_next_execution(frequency: str) -> str:
    """Calculate next execution time based on frequency."""
    now = datetime.utcnow()
    frequency_map = {
        "15min": timedelta(minutes=15),
        "30min": timedelta(minutes=30),
        "1hour": timedelta(hours=1),
        "3hours": timedelta(hours=3),
        "6hours": timedelta(hours=6),
        "12hours": timedelta(hours=12),
        "24hours": timedelta(hours=24),
    }
    delta = frequency_map.get(frequency, timedelta(hours=1))
    return (now + delta).isoformat()

async def send_discord_notification(webhook_url: str, title: str, description: str, color: int = 5814783):
    """Send a notification to Discord via webhook."""
    async with httpx.AsyncClient() as client:
        payload = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "GradEnt AI Autonomous Mode"
                }
            }]
        }
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()

async def run_autonomous_agent():
    """Execute the autonomous agent workflow."""
    logger.info("Starting autonomous agent execution")
    
    try:
        # Import executor agent
        from agents.executor_agent.agent import ExecutorAgent
        
        # Create config
        config = _require_agent_config()
        
        # Initialize executor agent
        executor = ExecutorAgent(config)
        
        # Run the agent
        result = await executor.execute()
        
        # Update last execution time
        AUTONOMOUS_CONFIG["last_execution"] = datetime.utcnow().isoformat()
        AUTONOMOUS_CONFIG["next_execution"] = calculate_next_execution(AUTONOMOUS_CONFIG["frequency"])
        
        # Send Discord notification if configured
        if AUTONOMOUS_CONFIG["discord_webhook"]:
            await send_discord_notification(
                AUTONOMOUS_CONFIG["discord_webhook"],
                "Autonomous Agent Completed",
                f"Tasks completed successfully!\n\nNext execution: {AUTONOMOUS_CONFIG['next_execution']}"
            )
        
        logger.info(f"Autonomous agent execution completed: {result}")
        
    except Exception as e:
        logger.error(f"Autonomous agent execution failed: {e}")
        
        # Send error notification if configured
        if AUTONOMOUS_CONFIG["discord_webhook"]:
            await send_discord_notification(
                AUTONOMOUS_CONFIG["discord_webhook"],
                "Autonomous Agent Error",
                f"Execution failed: {str(e)}",
                color=15158332  # Red color
            )

async def start_autonomous_scheduler():
    """Background task that runs the autonomous agent on schedule."""
    logger.info("Starting autonomous scheduler")
    
    while AUTONOMOUS_CONFIG["enabled"]:
        try:
            # Wait until next execution time
            next_exec = datetime.fromisoformat(AUTONOMOUS_CONFIG["next_execution"])
            now = datetime.utcnow()
            
            if now >= next_exec:
                # Run the agent
                await run_autonomous_agent()
            else:
                # Sleep until next execution
                sleep_seconds = (next_exec - now).total_seconds()
                await asyncio.sleep(min(sleep_seconds, 60))  # Check every minute
                
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying
```

### 4. Startup Hook

Add to `app/main.py` startup:

```python
@app.on_event("startup")
async def startup_event():
    """Initialize autonomous scheduler on startup."""
    if AUTONOMOUS_CONFIG["enabled"]:
        asyncio.create_task(start_autonomous_scheduler())
```

### 5. Executor Agent Requirements

The executor agent (`agents/executor_agent/agent.py`) should:
- Have an `execute()` method that runs the full workflow
- Automatically fetch context (assignments, calendar, etc.)
- Run planning workflows
- Execute tasks without user prompts
- Return a summary of what was done

Example structure:
```python
class ExecutorAgent:
    def __init__(self, config: Configuration):
        self.config = config
    
    async def execute(self) -> Dict[str, Any]:
        """Run autonomous execution."""
        results = {}
        
        # 1. Assess assignments
        assignments = await self.fetch_assignments()
        results["assessments"] = await self.assess_assignments(assignments)
        
        # 2. Generate suggestions
        results["suggestions"] = await self.generate_suggestions()
        
        # 3. Schedule study sessions
        results["scheduled"] = await self.schedule_sessions()
        
        return results
```

## Frontend Integration (Already Complete)

- ✅ Autonomous Mode UI component
- ✅ Configuration management
- ✅ Discord webhook testing
- ✅ Manual trigger button
- ✅ Status display

## Testing

1. **Test Configuration**:
   ```bash
   curl -X GET http://localhost:8000/api/autonomous/config
   ```

2. **Update Configuration**:
   ```bash
   curl -X PUT http://localhost:8000/api/autonomous/config \
     -H "Content-Type: application/json" \
     -d '{"enabled": true, "frequency": "1hour", "discord_webhook": "..."}'
   ```

3. **Manual Trigger**:
   ```bash
   curl -X POST http://localhost:8000/api/autonomous/execute
   ```

4. **Test Webhook**:
   ```bash
   curl -X POST http://localhost:8000/api/autonomous/test-webhook \
     -H "Content-Type: application/json" \
     -d '{"webhook_url": "https://discord.com/api/webhooks/..."}'
   ```

## Dependencies

Add to `pyproject.toml`:
```toml
[tool.poetry.dependencies]
httpx = "^0.24.0"  # For Discord webhook HTTP requests
```

## Security Considerations

1. **Validate webhook URLs**: Ensure they're Discord webhooks
2. **Rate limiting**: Prevent excessive executions
3. **Error handling**: Graceful degradation if executor fails
4. **Logging**: Track all autonomous executions
5. **User permissions**: If multi-user, ensure proper isolation

## Next Steps

1. Implement the backend endpoints in `app/main.py`
2. Create/update the executor agent to support autonomous mode
3. Add database schema if needed
4. Test the full flow
5. Deploy and monitor

