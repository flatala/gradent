"""Shared configuration for the LangGraph template."""
import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Annotated, Optional

from langchain_core.runnables import RunnableConfig, ensure_config


def _load_model_config() -> dict:
    """Load model configuration from JSON file."""
    config_path = Path(__file__).parent.parent / "model_config.json"
    if not config_path.exists():
        return {
            "orchestrator_model": "gpt-4o",
            "text_model": "gpt-4o-mini",
        }

    with open(config_path) as f:
        config = json.load(f)

    return {
        "orchestrator_model": config.get("orchestrator_model", "gpt-4o"),
        "text_model": config.get("text_model", "gpt-4o-mini"),
    }


@dataclass(kw_only=True)
class Configuration:
    """Shared configuration for all agents and workflows.

    This configuration provides:
    - OpenAI API key from environment
    - Two model configurations: orchestrator and text
    - Dependency injection via from_runnable_config()
    """

    # API KEY
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY"),
        metadata={"description": "OpenAI API key"}
    )

    # Optional base URL for OpenAI-compatible APIs (e.g., self-hosted gateways)
    openai_base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL"),
        metadata={"description": "Override base URL for OpenAI-compatible API (e.g. http://host:port/v1)"}
    )

    # Networking controls
    openai_timeout: int = field(
        default_factory=lambda: int(os.getenv("OPENAI_TIMEOUT", "60")),
        metadata={"description": "HTTP timeout (seconds) for LLM calls"}
    )
    openai_max_retries: int = field(
        default_factory=lambda: int(os.getenv("OPENAI_MAX_RETRIES", "1")),
        metadata={"description": "Max retries for LLM calls"}
    )

    # MODELS
    orchestrator_model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default_factory=lambda: _load_model_config().get("orchestrator_model", "gpt-4o"),
        metadata={"description": "OpenAI model for orchestration (e.g., gpt-4o)"}
    )

    text_model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default_factory=lambda: _load_model_config().get("text_model", "gpt-4o-mini"),
        metadata={"description": "OpenAI model for text generation (e.g., gpt-4o-mini)"}
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create Configuration from RunnableConfig for dependency injection."""
        cfg = ensure_config(config or {})
        data = cfg.get("configurable", {})
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in fields(cls)}})

    def validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment."
            )
