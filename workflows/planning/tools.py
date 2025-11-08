"""Tools for the planning workflow."""
import os
from typing import Annotated, Optional

from langchain_tavily import TavilySearch
from langchain_core.tools import tool, InjectedToolArg
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from shared.config import Configuration

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
        global _tavily_search
        if _tavily_search is None:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                return (
                    "Search unavailable: set TAVILY_API_KEY in your environment or .env."
                )
        
            _tavily_search = TavilySearch(max_results=5, tavily_api_key=api_key)


        results = await _tavily_search.ainvoke({"query": query})
        return str(results)

    except Exception as e:
        return f"Search failed: {str(e)}"