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
from .prompts import EXECUTOR_SYSTEM_PROMPT, SCHEDULE_MEETING_TASK_PROMPT, CONTEXT_UPDATE_AND_ASSESS_TASK_PROMPT
from datetime import datetime, timedelta
from agents.shared.workflow_tools import (
    run_scheduler_workflow,
    assess_assignment,
    run_context_update,
    get_unassessed_assignments,
)

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

    
    async def run_context_update_and_assess(
        self,
        user_id: int,
        auto_schedule: bool = True,
    ) -> Dict[str, Any]:
        """Update context from LMS, assess new/changed assignments, and schedule study sessions.

        Uses an LLM agent with tools to autonomously orchestrate the workflow.

        Args:
            user_id: Database user ID
            auto_schedule: If True, agent will automatically schedule study sessions

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
                auto_schedule=auto_schedule
            )

            tools = [run_context_update, get_unassessed_assignments, assess_assignment, run_scheduler_workflow]

            prompt = ChatPromptTemplate.from_messages([
                ("system", EXECUTOR_SYSTEM_PROMPT),
                ("human", task_prompt),
                MessagesPlaceholder("agent_scratchpad"),
            ])

            agent = create_openai_tools_agent(self.llm, tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

            # Execute the agent
            _logger.info("EXECUTOR: Running LLM agent with task prompt...")
            agent_result = await agent_executor.ainvoke({"input": task_prompt})

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