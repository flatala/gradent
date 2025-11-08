"""LangChain callbacks for request introspection."""
from __future__ import annotations

import json
import logging
from typing import Any, List

from langchain_core.callbacks import BaseCallbackHandler

_logger = logging.getLogger("chat")


def _preview(text: Any, limit: int = 300) -> str:
    try:
        s = str(text)
        return s if len(s) <= limit else s[:limit] + "... [truncated]"
    except Exception:
        return "[unprintable]"


class ChatMessagesLogger(BaseCallbackHandler):
    """Logs roles and key fields of messages on chat model start.

    Useful to verify proper tool_call → tool sequencing with OpenAI-compatible backends.
    """

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: List[List[dict[str, Any]]],
        run_id: str,
        parent_run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        if not _logger.handlers:
            return  # logging disabled
        try:
            # messages is a list of message lists (for multiple generations); take the first
            batch = messages[0] if messages else []
            compact = []
            tool_calls_present = False
            for m in batch:
                role = m.get("role") or m.get("type") or "?"
                entry = {"role": role}
                if role == "assistant" and m.get("tool_calls"):
                    tool_calls_present = True
                    # log tool names only
                    names = [tc.get("function", {}).get("name") for tc in m.get("tool_calls", [])]
                    entry["tool_calls"] = names
                if role == "tool":
                    entry["tool_call_id"] = m.get("tool_call_id")
                # include small preview of content
                if m.get("content") and isinstance(m["content"], str):
                    entry["content"] = _preview(m["content"], 180)
                compact.append(entry)
            _logger.info("LLM REQ MESSAGES: %s", json.dumps(compact, ensure_ascii=False))
            if tool_calls_present:
                _logger.info("LLM REQ HAS assistant.tool_calls preceding any tool messages")
        except Exception:
            # best-effort logging; never break the run
            pass

