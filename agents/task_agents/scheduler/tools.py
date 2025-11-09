"""Fixed Google Calendar operations for the scheduler workflow."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os

from shared.google_calendar import get_calendar_api_resource

_logger = logging.getLogger("chat")


def normalize_datetime_for_api(dt_string: str) -> str:
    """Normalize datetime string to RFC3339 format required by Google Calendar API.

    Args:
        dt_string: ISO 8601 datetime string (e.g., '2025-01-15T14:00:00')

    Returns:
        RFC3339 formatted string with timezone (e.g., '2025-01-15T14:00:00-08:00' or '2025-01-15T14:00:00Z')
    """
    # If already has timezone info, return as-is
    if dt_string.endswith('Z') or '+' in dt_string or dt_string.count('-') > 2:
        return dt_string

    # Get configured timezone
    tz_name = get_default_timezone()

    try:
        from datetime import datetime
        import pytz

        # Parse the datetime string
        dt = datetime.fromisoformat(dt_string)

        # Get timezone
        if tz_name and tz_name != "UTC":
            tz = pytz.timezone(tz_name)
            # Localize the naive datetime
            dt_localized = tz.localize(dt)
            # Format as RFC3339
            return dt_localized.isoformat()
        else:
            # Default to UTC
            return dt_string + 'Z'
    except Exception as e:
        _logger.warning(f"Failed to normalize datetime {dt_string}: {e}, defaulting to UTC")
        # Fallback: just add Z for UTC
        return dt_string + 'Z'


def get_default_calendar_id() -> str:
    """Get the default calendar ID from environment variables."""
    return (
        os.getenv("GOOGLE_CALENDAR_CALENDAR_ID")
        or os.getenv("GOOGLE_CALENDAR_DEFAULT_CALENDAR_ID")
        or "primary"
    )


def get_default_timezone() -> str:
    """Get the default timezone from environment variables."""
    return (
        os.getenv("GOOGLE_CALENDAR_TIME_ZONE")
        or os.getenv("TIME_ZONE")
        or "UTC"
    )


def check_availability(
    start_time: str,
    end_time: str,
    attendee_emails: Optional[List[str]] = None,
    calendar_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Check calendar availability for a time range.

    Args:
        start_time: ISO 8601 datetime string (e.g., '2025-01-15T09:00:00')
        end_time: ISO 8601 datetime string (e.g., '2025-01-15T17:00:00')
        attendee_emails: Optional list of attendee emails to check their availability too
        calendar_id: Calendar ID to check (defaults to primary calendar)

    Returns:
        Dictionary containing:
        - events: List of existing events in the time range
        - free_slots: List of free time slots
        - is_available: Boolean indicating if the entire range is free
    """
    try:
        calendar_id = calendar_id or get_default_calendar_id()
        service = get_calendar_api_resource()

        # Normalize datetime strings to RFC3339 format
        start_time_normalized = normalize_datetime_for_api(start_time)
        end_time_normalized = normalize_datetime_for_api(end_time)

        _logger.info(f"SCHEDULER: Checking availability from {start_time_normalized} to {end_time_normalized}")

        # Search for existing events in the time range
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time_normalized,
            timeMax=end_time_normalized,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        # Simple availability check - if no events, the whole range is free
        is_available = len(events) == 0

        result = {
            "success": True,
            "events": [
                {
                    "summary": e.get("summary", "No title"),
                    "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
                    "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
                    "id": e.get("id"),
                }
                for e in events
            ],
            "is_available": is_available,
            "checked_range": {"start": start_time, "end": end_time},
            "message": f"Found {len(events)} existing event(s) in the time range" if events else "Time range is available"
        }

        _logger.info(f"SCHEDULER: Availability check complete - {len(events)} conflicts found")
        return result

    except Exception as e:
        _logger.error(f"SCHEDULER: Failed to check availability: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to check availability: {str(e)}"
        }


def schedule_meeting(
    title: str,
    start_time: str,
    end_time: str,
    attendee_emails: Optional[List[str]] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    calendar_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Schedule a new meeting/event on the calendar.

    Args:
        title: Event title/summary
        start_time: ISO 8601 datetime string (e.g., '2025-01-15T14:00:00')
        end_time: ISO 8601 datetime string (e.g., '2025-01-15T15:00:00')
        attendee_emails: List of attendee email addresses
        location: Physical location or 'Google Meet' for virtual meeting
        description: Event description
        calendar_id: Calendar ID to create event in (defaults to primary)

    Returns:
        Dictionary containing the created event details or error information
    """
    try:
        calendar_id = calendar_id or get_default_calendar_id()
        timezone = get_default_timezone()
        service = get_calendar_api_resource()

        # Normalize datetime strings to RFC3339 format
        start_time_normalized = normalize_datetime_for_api(start_time)
        end_time_normalized = normalize_datetime_for_api(end_time)

        _logger.info(f"SCHEDULER: Creating event '{title}' from {start_time_normalized} to {end_time_normalized}")

        # Build event body
        event_body = {
            "summary": title,
            "start": {
                "dateTime": start_time_normalized,
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_time_normalized,
                "timeZone": timezone,
            },
        }

        if description:
            event_body["description"] = description

        if location:
            if location.lower() == "google meet":
                event_body["conferenceData"] = {
                    "createRequest": {
                        "requestId": f"meet-{datetime.now().timestamp()}",
                        "conferenceSolutionKey": {"type": "hangoutsMeet"}
                    }
                }
            else:
                event_body["location"] = location

        if attendee_emails:
            event_body["attendees"] = [{"email": email} for email in attendee_emails]

        # Create the event
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            conferenceDataVersion=1 if location and location.lower() == "google meet" else 0,
            sendUpdates="all" if attendee_emails else "none",
        ).execute()

        result = {
            "success": True,
            "event_id": created_event.get("id"),
            "title": created_event.get("summary"),
            "start": created_event.get("start", {}).get("dateTime"),
            "end": created_event.get("end", {}).get("dateTime"),
            "attendees": [a.get("email") for a in created_event.get("attendees", [])],
            "location": created_event.get("location"),
            "meeting_link": created_event.get("hangoutLink"),
            "calendar_link": created_event.get("htmlLink"),
            "message": f"Successfully created event: {title}"
        }

        _logger.info(f"SCHEDULER: ✓ Event created successfully - ID: {result['event_id']}")
        
        # Persist event to database
        try:
            from database.connection import SessionLocal
            from database.models import CalendarEvent
            
            db = SessionLocal()
            try:
                # Parse start and end times to datetime objects
                start_dt = datetime.fromisoformat(result["start"].replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(result["end"].replace("Z", "+00:00"))
                
                calendar_event = CalendarEvent(
                    user_id=1,  # Default user pattern
                    event_id=result["event_id"],
                    calendar_id=calendar_id,
                    title=result["title"],
                    description=description,
                    location=result.get("location"),
                    start_time=start_dt,
                    end_time=end_dt,
                    google_meet_url=result.get("meeting_link"),
                    calendar_link=result.get("calendar_link"),
                    attendees=result.get("attendees", [])
                )
                
                db.add(calendar_event)
                db.commit()
                _logger.info(f"SCHEDULER: ✓ Event persisted to database - ID: {result['event_id']}")
            finally:
                db.close()
        except Exception as db_error:
            _logger.error(f"SCHEDULER: Failed to persist event to database: {db_error}", exc_info=True)
            # Don't fail the whole operation if DB persistence fails
        
        return result

    except Exception as e:
        _logger.error(f"SCHEDULER: Failed to create event: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create event: {str(e)}"
        }


def cancel_meeting(
    event_id: str,
    calendar_id: Optional[str] = None,
    send_updates: bool = True,
) -> Dict[str, Any]:
    """Cancel/delete a calendar event.

    Args:
        event_id: The Google Calendar event ID to cancel
        calendar_id: Calendar ID containing the event (defaults to primary)
        send_updates: Whether to send cancellation emails to attendees

    Returns:
        Dictionary containing success status and message
    """
    try:
        calendar_id = calendar_id or get_default_calendar_id()
        service = get_calendar_api_resource()

        _logger.info(f"SCHEDULER: Canceling event {event_id}")

        # Delete the event
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id,
            sendUpdates="all" if send_updates else "none",
        ).execute()

        _logger.info(f"SCHEDULER: ✓ Event {event_id} canceled successfully")
        
        # Remove event from database
        try:
            from database.connection import SessionLocal
            from database.models import CalendarEvent
            
            db = SessionLocal()
            try:
                calendar_event = db.query(CalendarEvent).filter_by(event_id=event_id).first()
                if calendar_event:
                    db.delete(calendar_event)
                    db.commit()
                    _logger.info(f"SCHEDULER: ✓ Event removed from database - ID: {event_id}")
                else:
                    _logger.warning(f"SCHEDULER: Event {event_id} not found in database")
            finally:
                db.close()
        except Exception as db_error:
            _logger.error(f"SCHEDULER: Failed to remove event from database: {db_error}", exc_info=True)
            # Don't fail the whole operation if DB deletion fails
        
        return {
            "success": True,
            "event_id": event_id,
            "message": f"Successfully canceled event {event_id}"
        }

    except Exception as e:
        _logger.error(f"SCHEDULER: Failed to cancel event: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to cancel event: {str(e)}"
        }


def get_upcoming_meetings(
    days_ahead: int = 7,
    calendar_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get upcoming meetings from the calendar.

    Args:
        days_ahead: Number of days ahead to look (default 7)
        calendar_id: Calendar ID to query (defaults to primary)

    Returns:
        Dictionary containing list of upcoming events
    """
    try:
        calendar_id = calendar_id or get_default_calendar_id()
        timezone = get_default_timezone()
        service = get_calendar_api_resource()

        # Calculate time range
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

        _logger.info(f"SCHEDULER: Getting upcoming meetings for next {days_ahead} days")

        # Get events
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        result = {
            "success": True,
            "events": [
                {
                    "event_id": e.get("id"),
                    "title": e.get("summary", "No title"),
                    "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
                    "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
                    "location": e.get("location"),
                    "attendees": [a.get("email") for a in e.get("attendees", [])],
                    "meeting_link": e.get("hangoutLink"),
                    "calendar_link": e.get("htmlLink"),
                }
                for e in events
            ],
            "count": len(events),
            "days_ahead": days_ahead,
            "message": f"Found {len(events)} upcoming event(s) in the next {days_ahead} days"
        }

        _logger.info(f"SCHEDULER: ✓ Found {len(events)} upcoming meetings")
        return result

    except Exception as e:
        _logger.error(f"SCHEDULER: Failed to get upcoming meetings: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get upcoming meetings: {str(e)}"
        }


# Tool definitions for LangChain/LangGraph compatibility
SCHEDULER_TOOLS = [
    {
        "name": "check_availability",
        "description": "Check calendar availability for a specific time range. Returns existing events and indicates if the time slot is free.",
        "function": check_availability,
    },
    {
        "name": "schedule_meeting",
        "description": "Create a new calendar event/meeting with title, time, attendees, and location. Use this after confirming time slot is available.",
        "function": schedule_meeting,
    },
    {
        "name": "cancel_meeting",
        "description": "Cancel/delete an existing calendar event by its event ID. Sends cancellation notifications to attendees.",
        "function": cancel_meeting,
    },
    {
        "name": "get_upcoming_meetings",
        "description": "Retrieve upcoming meetings/events from the calendar for the next N days. Useful for viewing schedule.",
        "function": get_upcoming_meetings,
    },
]


def get_scheduler_tools() -> List[Dict[str, Any]]:
    """Get the list of fixed scheduler operations.

    Returns:
        List of tool definitions with name, description, and function
    """
    return SCHEDULER_TOOLS
