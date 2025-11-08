"""Google Calendar tools using LangChain's CalendarToolkit - SIMPLIFIED!"""
import logging
from typing import List
from langchain_google_community.calendar.toolkit import CalendarToolkit
from shared.google_calendar import get_calendar_api_resource

_logger = logging.getLogger("chat")

# Global cache for loaded tools
_loaded_tools: List = None


def load_calendar_tools() -> List:
    """Load Google Calendar tools using LangChain's CalendarToolkit.

    This is MUCH simpler than manually implementing tools!
    The toolkit provides pre-built tools for:
    - Creating calendar events
    - Searching/listing events
    - Updating events
    - Deleting events

    Returns:
        List of LangChain-compatible Google Calendar tools

    Raises:
        Exception: If authentication fails or credentials.json is missing
    """
    global _loaded_tools

    if _loaded_tools is None:
        _logger.info("SCHEDULER TOOLS: Loading calendar tools for the first time...")

        try:
            # Get authenticated API resource
            _logger.info("SCHEDULER TOOLS: Getting calendar API resource...")
            api_resource = get_calendar_api_resource()
            _logger.info("SCHEDULER TOOLS: ✓ API resource created successfully")

            # Create toolkit with the API resource
            _logger.info("SCHEDULER TOOLS: Creating CalendarToolkit...")
            toolkit = CalendarToolkit(api_resource=api_resource)

            # Get all the tools from the toolkit
            _logger.info("SCHEDULER TOOLS: Getting tools from toolkit...")
            _loaded_tools = toolkit.get_tools()
            _logger.info(f"SCHEDULER TOOLS: ✓ Loaded {len(_loaded_tools)} tools successfully")

            # Log tool details
            for tool in _loaded_tools:
                _logger.info(f"SCHEDULER TOOLS:   - {tool.name}: {tool.description[:100]}...")

        except Exception as e:
            _logger.error(f"SCHEDULER TOOLS: ✗ Failed to load tools: {e}", exc_info=True)
            raise
    else:
        _logger.info(f"SCHEDULER TOOLS: Using cached tools ({len(_loaded_tools)} tools)")

    return _loaded_tools
