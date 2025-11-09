"""Main conversational agent that can invoke workflow subgraphs."""
from typing import List
import logging
from pathlib import Path
import json

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from shared.config import Configuration
from shared.utils import get_orchestrator_llm
from agents.shared.workflow_tools import (
    run_scheduler_workflow,
    assess_assignment,
    generate_suggestions,
    run_exam_api_workflow,
)
from .prompts import SYSTEM_PROMPT

_logger = logging.getLogger("chat")


def _coerce_text(message: AIMessage) -> str:
    """Extract plain text from an AIMessage-like object robustly."""
    # Standard path: direct string content
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content
    # If content is structured (list of parts), try to collect text parts
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text" and part.get("text"):
                    parts.append(part["text"])
                elif "content" in part and isinstance(part["content"], str):
                    parts.append(part["content"])
        if parts:
            return "\n".join(parts).strip()
    # Some providers put function/tool calls in additional_kwargs with empty content
    addl = getattr(message, "additional_kwargs", {}) or {}
    tool_calls = addl.get("tool_calls") or []
    if tool_calls:
        texts = []
        for tc in tool_calls:
            fn = (tc or {}).get("function", {})
            name = fn.get("name")
            args = fn.get("arguments")
            if name or args:
                texts.append(f"Requested tool call: {name} {args}")
        if texts:
            return "\n".join(texts)
    return ""

def enable_chat_logging(level: int = logging.INFO, to_console: bool = True, to_file: bool = True) -> None:
    """Enable chat logging on demand.

    Adds console and file handlers to the 'chat' logger. Safe to call multiple times.
    """
    _logger.setLevel(level)
    if _logger.handlers:
        return
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    if to_file:
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "chat.log", encoding="utf-8")
        fh.setFormatter(fmt)
        _logger.addHandler(fh)
    if to_console:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        _logger.addHandler(sh)


def _safe_preview(text: str, limit: int = 2000) -> str:
    try:
        if text is None:
            return ""
        s = str(text)
        return s if len(s) <= limit else s[:limit] + "... [truncated]"
    except Exception:
        return "[unprintable]"


def create_main_agent(config: Configuration) -> AgentExecutor:
    """Create the main conversational agent.

    This agent:
    - Uses OpenAI orchestrator model for reasoning
    - Has access to workflow invocation tools
    - Maintains conversation history
    - Can handle multi-turn dialogues

    Args:
        config: Configuration with API keys and model settings

    Returns:
        AgentExecutor configured with tools and prompts
    """
    # Get the LLM
    llm = get_orchestrator_llm(config)

    # Define tools
    tools: List[BaseTool] = [
        run_scheduler_workflow,
        assess_assignment,
        generate_suggestions,
        run_exam_api_workflow,
    ]

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # Create the agent
    agent = create_openai_tools_agent(llm, tools, prompt)

    # Create executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=10,
    )

    return agent_executor


class MainAgent:
    """Wrapper class for the main conversational agent with chat history."""

    def __init__(self, config: Configuration):
        """Initialize the main agent.

        Args:
            config: Configuration with API keys and model settings
        """
        self.config = config
        self.agent = create_main_agent(config)
        self.chat_history = []
        _logger.info("Agent initialized with models - orchestrator=%s, text=%s", config.orchestrator_model, config.text_model)

    async def chat(self, user_message: str, *, config: dict | None = None) -> str:
        """Send a message to the agent and get a response.

        Args:
            user_message: The user's message
            config: Optional LangChain runnable configuration (callbacks, tags, etc.)

        Returns:
            The agent's response
        """
        # Always use the tools-enabled agent; it decides when to call tools
        _logger.info("USER: %s", _safe_preview(user_message))
        _logger.info("ROUTE: tools-agent")
        _logger.info("AGENT INPUT: %s", json.dumps({"input": user_message, "chat_history_len": len(self.chat_history)}))
        invoke_config = config or {}
        result = await self.agent.ainvoke(
            {
                "input": user_message,
                "chat_history": self.chat_history,
            },
            config=invoke_config,
        )
        response = result.get("output", "")
        _logger.info("AGENT OUTPUT: %s", _safe_preview(response))

        # Update chat history
        self.chat_history.append(HumanMessage(content=user_message))
        if response and response.strip():
            self.chat_history.append(AIMessage(content=response))
        _logger.info("ASSISTANT: %s", _safe_preview(response))

        return response

    def reset_history(self):
        """Clear the chat history."""
        self.chat_history = []
