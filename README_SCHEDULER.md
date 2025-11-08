# Scheduler Workflow - Simplified with LangChain CalendarToolkit

## ✅ Now Using LangChain's Built-in Google Calendar Tools!

Much simpler than before - we're using LangChain's `CalendarToolkit` instead of manually building tools.

---

## What You Need

### 1. Install Dependencies

```bash
poetry install
```

**Single package:** `langchain-google-community` (provides CalendarToolkit)

### 2. Set Up Google OAuth (One-Time, ~10 min)

See `GOOGLE_OAUTH_SETUP.md` for complete guide, or quick version:

**Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable **Google Calendar API**
4. Create **OAuth credentials** (Desktop app type)
5. Download `credentials.json` → Place in project root
6. Done! Browser will open for auth on first run

### 3. Test It

```bash
poetry install
python main.py
```

Ask:
```
Schedule a 30-minute meeting tomorrow at 2pm
```

**First time:** Browser opens → Authorize → Meeting created
**Future runs:** Automatic!

---

## How It Works

### Before (Manual Implementation)
❌ 260+ lines of manual Google API code
❌ Had to implement each tool ourselves
❌ Complex error handling

### After (LangChain Toolkit)
✅ **12 lines** in `tools.py`
✅ Pre-built, tested tools
✅ Works out of the box

### Code Comparison

**Before:**
```python
@tool
async def create_calendar_event(title, start_time, end_time, ...):
    # 50+ lines of Google API calls
    service = get_calendar_service()
    event = {...}
    created_event = service.events().insert(...).execute()
    # Parse response, handle errors, etc.
```

**After:**
```python
from langchain_google_community.calendar.toolkit import CalendarToolkit

toolkit = CalendarToolkit(api_resource=get_calendar_api_resource())
tools = toolkit.get_tools()  # That's it!
```

---

## Available Tools (From Toolkit)

The toolkit provides pre-built tools for:
- ✅ **Creating events** with attendees & Google Meet
- ✅ **Searching/listing events**
- ✅ **Updating events**
- ✅ **Deleting events**

Your agent can use all of these autonomously!

---

## Architecture

```
User: "Schedule meeting with alice@example.com"
  ↓
Main Orchestrator → Scheduler Workflow
  ↓
[Check Auth] → credentials.json exists?
  ↓
[Agent] → LLM with CalendarToolkit tools
  ↓
Agent autonomously:
  - Searches for free times
  - Creates event
  - Adds attendees
  - Generates Google Meet link
  ↓
Returns: Event ID, meeting link, confirmation
```

---

## Files

**Key Files:**
- `shared/google_calendar.py` - OAuth handler (60 lines, down from 160!)
- `workflows/scheduler/tools.py` - **12 lines** using CalendarToolkit
- `workflows/scheduler/nodes.py` - Agent logic
- `workflows/scheduler/graph.py` - Workflow graph

**Dependencies:**
- `langchain-google-community` - That's it!

---

## OAuth Setup (Quick Version)

1. **Google Cloud Console** → New Project
2. **Enable API**: Google Calendar API
3. **Create Credentials**: OAuth 2.0 (Desktop app)
4. **Download** `credentials.json` → Project root
5. **Run workflow** → Browser opens → Authorize
6. **Token saved** as `token.pickle` → Auto-refreshes

Done! See `GOOGLE_OAUTH_SETUP.md` for detailed walkthrough.

---

## Example Usage

**Simple:**
```
"Schedule a 1-hour meeting tomorrow at 2pm"
→ ✓ Created event for Jan 15, 2pm
```

**With Attendees:**
```
"Schedule team standup with alice@x.com and bob@y.com, 30 min, tomorrow 10am, Google Meet"
→ ✓ Created with Google Meet link
→ ✓ Invites sent to Alice & Bob
```

**Smart Scheduling:**
```
"Find time for 2-hour meeting with 3 people, afternoons only"
→ Agent checks all calendars
→ Finds free afternoon slot
→ Creates event
→ ✓ Scheduled for Wed 2pm
```

---

## Troubleshooting

### "credentials.json not found"
Download OAuth credentials from Google Cloud Console (see `GOOGLE_OAUTH_SETUP.md`)

### "Calendar API not enabled"
Go to Google Cloud Console → APIs & Services → Library → Enable "Google Calendar API"

### Token expired
```bash
rm token.pickle  # Delete old token
python main.py   # Re-authorize
```

---

## Summary

| Aspect | Value |
|--------|-------|
| **Dependencies** | 1 package (`langchain-google-community`) |
| **Code** | 12 lines in `tools.py` |
| **Setup Time** | 10 minutes (one-time OAuth) |
| **Auth** | Automatic token refresh |
| **Tools** | All Calendar operations |
| **Agent** | Fully autonomous |

**Status:** ✅ Ready to use after OAuth setup!

**Next:** Follow `GOOGLE_OAUTH_SETUP.md` → Get credentials → Test!
