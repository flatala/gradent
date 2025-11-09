# Google Calendar OAuth Setup (5 Minutes)

This guide shows you how to set up OAuth for **personal calendar access** (no service account needed).

## Why OAuth Instead of Service Account?

✅ **OAuth Advantages:**
- Access YOUR personal calendar
- Can invite attendees to meetings
- Can create Google Meet links
- No Domain-Wide Delegation needed

❌ **Service Account Limitations:**
- Cannot invite attendees without Domain-Wide Delegation
- Cannot create Google Meet links reliably
- Requires sharing calendar with service account

---

## Step 1: Enable Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Go to **APIs & Services** → **Library**
4. Search for "Google Calendar API"
5. Click **Enable**

---

## Step 2: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. If prompted, configure OAuth consent screen:
   - User Type: **External**
   - App name: `My Calendar Scheduler` (or whatever you want)
   - User support email: your email
   - Developer contact: your email
   - Click **SAVE AND CONTINUE**
   - Scopes: Skip (click **SAVE AND CONTINUE**)
   - Test users: Add your email
   - Click **SAVE AND CONTINUE**
4. Back to Create OAuth Client ID:
   - Application type: **Desktop app**
   - Name: `Calendar Scheduler` (or whatever)
   - Click **CREATE**
5. Download the JSON file
6. **Rename it to `credentials.json`**
7. **Move it to your project root** (same directory as this README)

---

## Step 3: First-Time Authorization

The first time you run the scheduler, it will:

1. **Open your browser automatically**
2. Ask you to sign in with your Google account
3. Show a warning "This app isn't verified" - click **Advanced** → **Go to [App Name] (unsafe)**
4. Grant calendar permissions
5. **Save the token** to `token.pickle` for future use

After this, you won't need to authorize again unless you:
- Delete `token.pickle`
- Revoke access in Google Account settings
- Token expires after 7 days of inactivity

---

## Step 4: Test It

Run a simple test:

```bash
poetry run python -c "
from shared.google_calendar import get_calendar_api_resource, check_auth_status

# Check auth status
status = check_auth_status()
print(f'Auth status: {status}')

# If authenticated, test API call
if status['authenticated']:
    service = get_calendar_api_resource()
    print('✓ Successfully connected to Google Calendar!')
"
```

**First time:** Browser will open for authorization
**Subsequent times:** Uses saved token, no browser needed

---

## File Structure

After setup, you should have:

```
langgraph-template/
├── credentials.json    # OAuth client credentials (DO NOT commit)
├── token.pickle        # Your personal access token (DO NOT commit)
├── .gitignore          # Already ignores both files ✓
└── OAUTH_SETUP.md      # This file
```

Both `credentials.json` and `token.pickle` are in `.gitignore` to prevent accidental commits.

---

## Security Notes

⚠️ **Keep these files private:**
- `credentials.json` - OAuth client secret
- `token.pickle` - Your personal access token

✅ **Safe to share:**
- The setup instructions
- Your code (tokens are separate files)

🔒 **Token refresh:**
- Tokens auto-refresh when expired
- No manual intervention needed
- If refresh fails, delete `token.pickle` and re-authorize

---

## Troubleshooting

### "credentials.json not found"
→ Download OAuth credentials from Google Cloud Console (Step 2)
→ Rename to exactly `credentials.json`
→ Place in project root directory

### "Browser didn't open"
→ Copy the authorization URL from the terminal
→ Paste into your browser manually
→ Complete authorization

### "Token expired"
→ Run your app again - it will auto-refresh
→ If that fails, delete `token.pickle` and re-authorize

### "Access blocked"
→ Add your email to Test Users in OAuth consent screen
→ Make sure Calendar API is enabled

---

## Comparison with Service Account

| Feature | OAuth (This Setup) | Service Account |
|---------|-------------------|-----------------|
| Personal calendar | ✅ Yes | ❌ Must share manually |
| Invite attendees | ✅ Yes | ❌ Needs Domain-Wide Delegation |
| Google Meet links | ✅ Yes | ⚠️ Limited support |
| Setup complexity | Medium (one-time auth) | Medium (JSON key) |
| Token refresh | ✅ Automatic | N/A (key-based) |
| Best for | Personal use | Server automation |

---

## Next Steps

Once OAuth is set up:

1. ✅ Your scheduler can access your personal calendar
2. ✅ You can invite attendees to meetings
3. ✅ You can create Google Meet links automatically
4. ✅ Token auto-refreshes - no maintenance needed

Try scheduling a meeting with attendees:

```python
from workflows.scheduler.graph import scheduler_graph
from workflows.scheduler.state import SchedulerState

state = SchedulerState(
    meeting_name="Team Sync",
    duration_minutes=30,
    attendee_emails=["colleague@example.com"],
    location="Google Meet",  # Creates Meet link automatically!
    preferred_start="2025-01-15T14:00:00",
    preferred_end="2025-01-15T14:30:00",
)

result = await scheduler_graph.ainvoke(state)
print(f"Meeting scheduled: {result.scheduled_event.calendar_link}")
print(f"Google Meet: {result.scheduled_event.meeting_link}")
```

Now it will work! 🎉
