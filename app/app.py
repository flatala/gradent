from pathlib import Path
import sys

import chainlit as cl

# Ensure project root is importable when Chainlit loads this module directly
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.config import Configuration
from main_agent import MainAgent


def _build_config():
    """Create LangChain runnable config with Chainlit callbacks."""
    callback = cl.LangchainCallbackHandler()
    return {
        "callbacks": [callback],
        "configurable": {"thread_id": cl.context.session.id},
    }


@cl.on_chat_start
async def handle_start():
    """Initialize the LangGraph main agent when a session begins."""
    try:
        cfg = Configuration()
        cfg.validate()
    except ValueError as exc:
        await cl.Message(
            author="system",
            content=f"Configuration error: {exc}",
            type="error",
        ).send()
        return

    agent = MainAgent(cfg)
    cl.user_session.set("agent", agent)
    await cl.Message(
        author="assistant",
        content="Hi! I’m ready to help with planning, assignments, and scheduling.",
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Forward user messages to the LangGraph agent and return its response."""
    agent: MainAgent | None = cl.user_session.get("agent")
    if agent is None:
        await handle_start()
        agent = cl.user_session.get("agent")
        if agent is None:
            await cl.Message(
                author="system",
                content="Agent failed to initialize. Please check server logs.",
                type="error",
            ).send()
            return

    msg = cl.Message(author="assistant", content="")
    try:
        response_text = await agent.chat(
            message.content,
            config=_build_config(),
        )
        await msg.stream_token(response_text)
    except Exception as exc:  # pragma: no cover - best effort error surface
        await cl.Message(
            author="system",
            content=f"Error while generating response: {exc}",
            type="error",
        ).send()
        return

    await msg.send()


@cl.on_chat_end
async def handle_end():
    """Clear chat state when the session closes."""
    agent: MainAgent | None = cl.user_session.get("agent")
    if agent:
        agent.reset_history()