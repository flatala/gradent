"""Shared utilities for LLM creation."""
from typing import Optional

from langchain_openai import ChatOpenAI

from .config import Configuration
from .callbacks import ChatMessagesLogger


def _normalize_base_url(url: Optional[str]) -> Optional[str]:
    """Normalize user-provided base URL for OpenAI-compatible endpoints.

    - If it ends with "/chat/completions", strip that suffix.
    - Trim any trailing slash.
    """
    if not url:
        return url
    u = url.rstrip("/")
    if u.endswith("/chat/completions"):
        u = u[: -len("/chat/completions")]
    return u


def get_orchestrator_llm(cfg: Configuration) -> ChatOpenAI:
    """Get the orchestrator LLM instance.

    The orchestrator model is typically more capable and used for:
    - High-level reasoning and planning
    - Tool selection and workflow orchestration
    - Complex decision making

    Args:
        cfg: Configuration instance with API key and model settings

    Returns:
        ChatOpenAI instance configured for orchestration
    """
    return ChatOpenAI(
        model=cfg.orchestrator_model,
        api_key=cfg.openai_api_key,
        base_url=_normalize_base_url(cfg.openai_base_url),
        streaming=False,
        timeout=cfg.openai_timeout,
        max_retries=cfg.openai_max_retries,
        temperature=1.0,
        callbacks=[ChatMessagesLogger()],
    )


def get_text_llm(cfg: Configuration) -> ChatOpenAI:
    """Get the text generation LLM instance.

    The text model is typically faster/cheaper and used for:
    - Content generation and summarization
    - Data processing and transformation
    - Routine text tasks

    Args:
        cfg: Configuration instance with API key and model settings

    Returns:
        ChatOpenAI instance configured for text generation
    """
    return ChatOpenAI(
        model=cfg.text_model,
        api_key=cfg.openai_api_key,
        base_url=_normalize_base_url(cfg.openai_base_url),
        streaming=False,
        timeout=cfg.openai_timeout,
        max_retries=cfg.openai_max_retries,
        temperature=1.0,
        callbacks=[ChatMessagesLogger()],
    )
