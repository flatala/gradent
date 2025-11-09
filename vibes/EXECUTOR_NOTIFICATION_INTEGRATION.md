# 🔗 Integrating Executor Agent with Notifications

## What You Have

### Executor Agent (`agents/executor_agent/executor.py`)
- ✅ Fully working autonomous agent
- ✅ Uses LLM to orchestrate workflows
- ✅ Method: `run_context_update_and_assess(user_id, auto_schedule=True)`
- ✅ Uses tools: `run_context_update`, `assess_assignment`, `run_scheduler_workflow`
- ✅ Returns structured results (success, duration, output)

### Notification System
- ✅ `ToolCallTracker` tracks tool executions
- ✅ When `send_notifications=True`, sends to Discord/ntfy
- ✅ Already integrated in `app/main.py`

## How to Integrate

The **key insight**: The `AgentExecutor` in the executor agent accepts `callbacks`!

### Step 1: Update `execute_autonomous_agent()` in `app/main.py`

Replace the TODO section with actual executor agent:

```python
async def execute_autonomous_agent():
    """Actually run the autonomous agent with notifications."""
    ntfy_topic = AUTONOMOUS_CONFIG.get("ntfy_topic")
    discord_webhook = AUTONOMOUS_CONFIG.get("discord_webhook")
    
    logger.info("[AUTONOMOUS] Starting execution")
    
    # Send start notification
    if ntfy_topic:
        await send_ntfy_notification(
            "🤖 Autonomous agent started!\n\nChecking assignments from LMS, planning study sessions...",
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
    
    # ✅ Actually run the executor agent with callbacks!
    try:
        from agents.executor_agent.executor import ExecutorAgent
        
        executor = ExecutorAgent(config=AGENT_CONFIG)
        
        # Run the main workflow with notification callbacks
        # The tracker will automatically send notifications as tools execute
        result = await executor.run_context_update_and_assess(
            user_id=1,  # TODO: Get from config or user context
            auto_schedule=True,
            callbacks=[tracker]  # ← This is the magic! Tracker sees all tool calls
        )
        
        logger.info(f"[AUTONOMOUS] Executor result: {result}")
        
        # Send completion notification
        if ntfy_topic:
            if result.get("success"):
                await send_ntfy_notification(
                    f"✅ Autonomous agent completed!\n\n{result.get('agent_output', 'Task completed successfully')}",
                    topic=ntfy_topic,
                    title="✅ Agent Completed",
                    priority=3,
                    tags=["white_check_mark", "tada", "books"]
                )
            else:
                await send_ntfy_notification(
                    f"❌ Autonomous agent failed\n\n{result.get('error', 'Unknown error')}",
                    topic=ntfy_topic,
                    title="❌ Agent Failed",
                    priority=5,
                    tags=["x", "warning"]
                )
        
    except Exception as e:
        logger.error(f"[AUTONOMOUS] Execution error: {e}", exc_info=True)
        
        # Send error notification
        if ntfy_topic:
            await send_ntfy_notification(
                f"❌ Autonomous agent crashed\n\n{str(e)}",
                topic=ntfy_topic,
                title="❌ Critical Error",
                priority=5,
                tags=["x", "fire"]
            )
        raise
    
    logger.info("[AUTONOMOUS] Execution completed")
```

### Wait, There's a Problem!

Looking at the executor agent code:
```python
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
result = await agent_executor.ainvoke({"input": task_prompt})
```

The executor creates its OWN `AgentExecutor` inside the method. We need to pass callbacks through!

### Step 2: Update `ExecutorAgent.run_context_update_and_assess()` to Accept Callbacks

Modify `/Users/alex.zheng/hackathon/gradent/agents/executor_agent/executor.py`:

```python
async def run_context_update_and_assess(
    self,
    user_id: int,
    auto_schedule: bool = True,
    callbacks: Optional[List] = None,  # ← Add this parameter
) -> Dict[str, Any]:
    """Update context from LMS, assess new/changed assignments, and schedule study sessions.

    Uses an LLM agent with tools to autonomously orchestrate the workflow.

    Args:
        user_id: Database user ID
        auto_schedule: If True, agent will automatically schedule study sessions
        callbacks: Optional list of LangChain callbacks (e.g., for notifications)

    Returns:
        Dict with success, context_update, assessments, scheduled_sessions, duration_ms
    """
    start_time = perf_counter()

    _logger.info(
        "EXECUTOR TASK: context_update_and_assess | user_id=%d | auto_schedule=%s",
        user_id,
        auto_schedule
    )

    try:
        task_prompt = CONTEXT_UPDATE_AND_ASSESS_TASK_PROMPT.format(
            user_id=user_id,
            auto_schedule_status='ENABLED' if auto_schedule else 'DISABLED'
        )

        tools = [run_context_update, get_unassessed_assignments, assess_assignment, run_scheduler_workflow]

        prompt = ChatPromptTemplate.from_messages([
            ("system", EXECUTOR_SYSTEM_PROMPT),
            ("human", task_prompt),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(self.llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        # Execute the agent with callbacks
        _logger.info("EXECUTOR: Running LLM agent with task prompt...")
        agent_result = await agent_executor.ainvoke(
            {"input": task_prompt},
            config={"callbacks": callbacks} if callbacks else {}  # ← Pass callbacks here
        )

        duration_ms = int((perf_counter() - start_time) * 1000)

        _logger.info("EXECUTOR: ✓ Agent completed | duration=%dms", duration_ms)

        return {
            "success": True,
            "agent_output": agent_result.get("output", ""),
            "duration_ms": duration_ms,
        }

    except Exception as e:
        duration_ms = int((perf_counter() - start_time) * 1000)
        _logger.error(
            "EXECUTOR: ✗ Task failed | error=%s | duration=%dms",
            str(e),
            duration_ms,
            exc_info=True
        )

        return {
            "success": False,
            "error": str(e),
            "duration_ms": duration_ms,
        }
```

## Complete Flow

```
User enables autonomous mode → FastAPI starts scheduler loop
                  ↓
Every hour, scheduler triggers execute_autonomous_agent()
                  ↓
Send "Agent Started" notification
                  ↓
Create ToolCallTracker(send_notifications=True)
                  ↓
Run ExecutorAgent.run_context_update_and_assess(callbacks=[tracker])
                  ↓
Agent uses tools:
  1. run_context_update → Tracker detects → 📱 Notification: "Context Updated"
  2. assess_assignment → Tracker detects → 📱 Notification: "Assignment Assessed"
  3. run_scheduler_workflow → Tracker detects → 📱 Notification: "Meeting Scheduled"
                  ↓
Executor returns result
                  ↓
Send "Agent Completed" notification with summary
                  ↓
User gets 5 notifications total:
  1. 🤖 Agent Started
  2. 📊 Context Updated
  3. 📝 Assignment Assessed
  4. 📅 Meeting Scheduled
  5. ✅ Agent Completed
```

## Tool Call Mapping

The executor uses these tools (already in `ToolCallTracker`!):

| Tool Function | Tracker Type | Notification |
|---------------|--------------|--------------|
| `run_scheduler_workflow` | `scheduler` | 📅 Schedule Meeting |
| `assess_assignment` | `assessment` | 📊 Assess Assignment |
| `run_context_update` | ❌ Not tracked yet | (need to add) |
| `get_unassessed_assignments` | ❌ Not tracked yet | (need to add) |

### Step 3: Add Missing Tools to ToolCallTracker

Update `app/main.py`:

```python
class ToolCallTracker(BaseCallbackHandler):
    # ... existing code ...
    
    def __init__(self, send_notifications: bool = False, discord_webhook: Optional[str] = None, ntfy_topic: Optional[str] = None):
        # ... existing code ...
        self.tool_map = {
            "run_scheduler_workflow": {"type": "scheduler", "name": "Schedule Meeting"},
            "assess_assignment": {"type": "assessment", "name": "Assess Assignment"},
            "generate_suggestions": {"type": "suggestions", "name": "Generate Suggestions"},
            "run_exam_api_workflow": {"type": "exam_generation", "name": "Generate Exam"},
            # ← Add these for executor agent
            "run_context_update": {"type": "context_update", "name": "Update LMS Context"},
            "get_unassessed_assignments": {"type": "query", "name": "Get Unassessed Assignments"},
        }
```

### Step 4: Add New Tool Types to Notification Formatter

Update `notifications/autonomous.py`:

```python
def _format_tool_result(tool_type: str, result: Dict[str, Any]) -> str:
    """Format tool result for Discord notification."""
    
    if tool_type == "scheduler":
        # ... existing code ...
    
    elif tool_type == "assessment":
        # ... existing code ...
    
    elif tool_type == "suggestions":
        # ... existing code ...
    
    elif tool_type == "exam_generation":
        # ... existing code ...
    
    # ← Add these new cases
    elif tool_type == "context_update":
        courses = result.get("courses_synced", 0)
        assignments = result.get("assignments_synced", 0)
        return f"**Context Update Complete**\n\n• Synced {courses} courses\n• Found {assignments} assignments"
    
    elif tool_type == "query":
        count = result.get("count", 0)
        return f"**Query Complete**\n\nFound {count} unassessed assignments"
    
    return "Task completed successfully! ✅"
```

And update the tool config mapping:

```python
async def send_tool_completion_notification(
    webhook_url: str,
    tool_type: str,
    tool_name: str,
    result: Dict[str, Any],
    ntfy_topic: Optional[str] = None,
) -> bool:
    # Icon and color mapping
    tool_config = {
        "scheduler": {"icon": "📅", "color": 3447003, "emoji": "calendar"},
        "assessment": {"icon": "📊", "color": 15844367, "emoji": "bar_chart"},
        "suggestions": {"icon": "💡", "color": 5763719, "emoji": "bulb"},
        "exam_generation": {"icon": "🧠", "color": 10181046, "emoji": "brain"},
        # ← Add these
        "context_update": {"icon": "🔄", "color": 5793266, "emoji": "arrows_counterclockwise"},
        "query": {"icon": "🔍", "color": 9807270, "emoji": "mag"},
    }
    # ... rest of function ...
```

## Summary of Changes

### 1. In `app/main.py`
- ✅ Update `execute_autonomous_agent()` to use real ExecutorAgent
- ✅ Pass `callbacks=[tracker]` to executor
- ✅ Add `run_context_update` and `get_unassessed_assignments` to tool_map

### 2. In `agents/executor_agent/executor.py`
- ✅ Add `callbacks` parameter to `run_context_update_and_assess()`
- ✅ Pass callbacks to `agent_executor.ainvoke()`

### 3. In `notifications/autonomous.py`
- ✅ Add `context_update` and `query` to tool config
- ✅ Add formatting for these tool types

## Testing

```bash
# Start backend
poetry run uvicorn app.main:app --reload

# Enable autonomous mode
curl -X PUT http://localhost:8000/api/autonomous/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "frequency": "15min",
    "ntfy_topic": "gradent-ai-test-123"
  }'

# Subscribe to notifications
open https://ntfy.sh/gradent-ai-test-123

# Manually trigger (for testing)
curl -X POST http://localhost:8000/api/autonomous/execute

# Watch notifications appear:
# 1. 🤖 Agent Started
# 2. 🔄 Update LMS Context
# 3. 🔍 Get Unassessed Assignments
# 4. 📊 Assess Assignment
# 5. 📅 Schedule Meeting
# 6. ✅ Agent Completed
```

That's it! The executor agent now automatically sends notifications through your existing system! 🎉

