"""Tools for the planning workflow."""
import os
from typing import Annotated, Optional

from langchain_tavily import TavilySearch
from langchain_core.tools import tool, InjectedToolArg
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from shared.config import Configuration

# Lazily initialized Tavily tool to ensure env is loaded
_tavily_search: Optional[TavilySearch] = None


@tool
async def web_search(query: str, *, config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Search the web for information using Tavily.

    Use this tool to find up-to-date information, research topics, or gather
    data from the internet.

    Args:
        query: The search query string
        config: Injected configuration (automatically provided)

    Returns:
        Search results with snippets and URLs
    """
    cfg = Configuration.from_runnable_config(config)

    try:
        # Initialize on first use so .env is loaded
        global _tavily_search
        if _tavily_search is None:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                return (
                    "Search unavailable: set TAVILY_API_KEY in your environment or .env."
                )
            # Pass API key explicitly to avoid discovery issues
            _tavily_search = TavilySearch(max_results=5, tavily_api_key=api_key)

        # Tavily search returns formatted results
        results = await _tavily_search.ainvoke({"query": query})
        return str(results)

    except Exception as e:
        return f"Search failed: {str(e)}"


@tool
def human_input(question: str) -> str:
    """Request input or feedback from a human.

    Use this tool when you need:
    - Clarification on requirements
    - User preferences or decisions
    - Validation of assumptions
    - Additional information only the user can provide

    Args:
        question: The question to ask the human

    Returns:
        The human's response
    """
    # Interrupt the workflow and wait for human input
    human_response = interrupt({"question": question})
    return human_response.get("data", "")
