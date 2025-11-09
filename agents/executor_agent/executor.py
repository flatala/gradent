"""Autonomous task executor for background operations.

ExecutorAgent handles autonomous workflow execution without user interaction.
It's designed for cron jobs, webhooks, and event-driven automation.

Key differences from MainAgent (chat):
- Uses LLM agent with task-specific prompts (not conversational)
- Returns structured results (dict) not conversational responses
- Designed for background/scheduled execution
- Logs progress instead of user-facing messages
- Each task method gets its own instruction prompt
"""
import logging
from typing import Dict, Any, Optional, List
from time import perf_counter

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_tools_agent, AgentExecutor

from shared.config import Configuration
from shared.utils import get_orchestrator_llm
from agents.task_agents.scheduler import scheduler_graph, SchedulerState
from .prompts import EXECUTOR_SYSTEM_PROMPT, SCHEDULE_MEETING_TASK_PROMPT

_logger = logging.getLogger("executor")


class ExecutorAgent:
    """Autonomous executor for background tasks and scheduled workflows.

    This agent uses an LLM with task-specific prompts to execute autonomous workflows:
    - System prompt defines overall executor role and capabilities
    - Each task method gets its own instruction prompt
    - Uses workflows and tools to complete tasks end-to-end
    - Returns structured results for logging/monitoring
    - No user interaction - fully autonomous

    Example usage:
        executor = ExecutorAgent(config)
        result = await executor.execute_schedule_meeting(
            meeting_name="Team Sync",
            duration_minutes=30,
            preferred_time="2025-01-15T14:00:00"
        )
        print(f"Scheduled: {result['event_id']}")
    """

    def __init__(self, config: Configuration):
        """Initialize the executor agent.

        Args:
            config: Configuration instance with model settings and API keys
        """
        self.config = config
        self.llm = get_orchestrator_llm(config)
        _logger.info("ExecutorAgent initialized with LLM: %s", config.orchestrator_model)

    async def execute_schedule_meeting(
        self,
        meeting_name: str,
        duration_minutes: int,
        preferred_time: str,
        topic: Optional[str] = None,
        attendee_emails: Optional[List[str]] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Autonomously schedule a meeting without user interaction.

        This is a demonstration of the executor pattern using LLM with task prompts.
        The agent receives a task-specific prompt and uses workflows to complete it.

        NOTE: This is a simple example. Real tasks like run_assignment_check()
        would orchestrate multiple workflows (ingestion → notify → schedule).

        Args:
            meeting_name: Title of the meeting
            duration_minutes: Meeting duration
            preferred_time: ISO 8601 datetime string (e.g., '2025-01-15T14:00:00')
            topic: Optional meeting topic/agenda
            attendee_emails: Optional list of attendee emails
            location: Optional location (use "Google Meet" for virtual)

        Returns:
            Dict with:
                - success: bool - Whether scheduling succeeded
                - event_id: str - Calendar event ID (if successful)
                - calendar_link: str - Link to calendar event (if successful)
                - meeting_link: str - Google Meet link if applicable (if successful)
                - error: str - Error message (if failed)
                - duration_ms: int - Execution time in milliseconds
        """
        start_time = perf_counter()

        _logger.info(
            "EXECUTOR TASK: schedule_meeting | meeting='%s' | duration=%d min | time=%s",
            meeting_name,
            duration_minutes,
            preferred_time
        )

        try:
            # Format task-specific instruction prompt
            task_prompt = SCHEDULE_MEETING_TASK_PROMPT.format(
                meeting_name=meeting_name,
                duration_minutes=duration_minutes,
                preferred_time=preferred_time,
                topic=topic or "Not specified",
                attendees=", ".join(attendee_emails) if attendee_emails else "None",
                location=location or "Not specified"
            )

            _logger.debug("EXECUTOR: Task prompt prepared, executing workflow directly...")

            # For this demo, we'll directly call the workflow
            # In future, you could use an LLM agent to interpret the task prompt
            # and decide which workflows to call in what order

            # Build full description
            description_parts = []
            if topic:
                description_parts.append(f"Topic: {topic}")
            full_description = "\n\n".join(description_parts) if description_parts else meeting_name

            # Create initial state for scheduler workflow
            initial_state = SchedulerState(
                meeting_name=meeting_name,
                topic=topic,
                event_description=full_description,
                duration_minutes=duration_minutes,
                attendee_emails=attendee_emails or [],
                location=location,
                preferred_start=preferred_time,
            )

            # Execute scheduler workflow
            result = await scheduler_graph.ainvoke(initial_state)

            duration_ms = int((perf_counter() - start_time) * 1000)

            # Check if scheduling succeeded
            if result.scheduled_event:
                event = result.scheduled_event
                _logger.info(
                    "EXECUTOR: ✓ Task completed successfully | event_id=%s | duration=%dms",
                    event.event_id,
                    duration_ms
                )

                return {
                    "success": True,
                    "event_id": event.event_id,
                    "title": event.title,
                    "start_time": event.start_time,
                    "end_time": event.end_time,
                    "calendar_link": event.calendar_link,
                    "meeting_link": event.meeting_link,
                    "attendees": event.attendees,
                    "location": event.location,
                    "duration_ms": duration_ms,
                    "task_prompt_used": True,  # Indicates task prompt was prepared
                }
            else:
                # Scheduling failed
                error_msg = result.reasoning or "Unknown error - no event created"
                _logger.warning(
                    "EXECUTOR: ✗ Task failed | reason=%s | duration=%dms",
                    error_msg,
                    duration_ms
                )

                return {
                    "success": False,
                    "error": error_msg,
                    "duration_ms": duration_ms,
                }

        except Exception as e:
            duration_ms = int((perf_counter() - start_time) * 1000)
            _logger.error(
                "EXECUTOR: ✗ Exception during task | error=%s | duration=%dms",
                str(e),
                duration_ms,
                exc_info=True
            )

            return {
                "success": False,
                "error": f"Exception: {str(e)}",
                "duration_ms": duration_ms,
            }

    # Future methods for complex autonomous workflows:

    # async def run_assignment_check(self) -> Dict[str, Any]:
    #     """Check for new assignments and auto-schedule study sessions.
    #
    #     This will:
    #     1. Call ingestion_workflow to scrape assignment portals
    #     2. Save new assignments to database
    #     3. Call notifier_workflow to send notifications
    #     4. Call scheduler_workflow to create study sessions
    #
    #     Returns:
    #         Dict with assignments_processed, notifications_sent, events_created
    #     """
    #     pass

    # async def run_daily_planning(self) -> Dict[str, Any]:
    #     """Daily planning routine - review schedule and optimize.
    #
    #     Returns:
    #         Dict with optimization suggestions and actions taken
    #     """
    #     pass
