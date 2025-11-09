# Environment Variables Configuration

## Notification Settings

### NTFY_DEFAULT_TOPIC
**Default:** `gradent-ai-test-123`

The default ntfy topic name for push notifications. Users can override this in the Autonomous Mode UI, but this sets the initial value.

**Usage:**
```bash
export NTFY_DEFAULT_TOPIC=gradent-ai-test-123
```

**Why this default?**
- Easy to test and demo
- Matches the test script (`./test_ntfy.sh`)
- Users can subscribe at: https://ntfy.sh/gradent-ai-test-123
- Users are encouraged to change it to their own unique topic

### DISCORD_WEBHOOK_URL (Optional)
Discord webhook for sending notifications.

**Usage:**
```bash
export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN
```

## Dispatcher Settings

### SUGGESTION_POLL_SECONDS
**Default:** `10`

How often (in seconds) the dispatcher checks for due suggestions.

### SUGGESTION_MAX_PER_CYCLE
**Default:** `1`

Maximum number of suggestions to process per polling cycle.

## Setting Environment Variables

### Development (.env file)
Create a `.env` file in the project root:

```bash
# Notifications
NTFY_DEFAULT_TOPIC=gradent-ai-test-123
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Dispatcher
SUGGESTION_POLL_SECONDS=10
SUGGESTION_MAX_PER_CYCLE=1
```

### Production
Set environment variables in your deployment platform:

**Heroku:**
```bash
heroku config:set NTFY_DEFAULT_TOPIC=my-prod-topic
```

**Docker:**
```bash
docker run -e NTFY_DEFAULT_TOPIC=my-prod-topic ...
```

**systemd:**
```ini
[Service]
Environment="NTFY_DEFAULT_TOPIC=my-prod-topic"
```

## Testing the Default Topic

The default topic `gradent-ai-test-123` is great for testing:

**Subscribe in browser:**
```
https://ntfy.sh/gradent-ai-test-123
```

**Test with curl:**
```bash
./test_ntfy.sh
```

**Subscribe on mobile:**
1. Download ntfy app
2. Add topic: `gradent-ai-test-123`
3. Click "Run Now" in the UI
4. Get notifications!

## Changing Topics

Users can change their ntfy topic in two ways:

1. **In the UI:** Autonomous Mode tab → Enter custom topic → Save
2. **Environment variable:** Set `NTFY_DEFAULT_TOPIC` before starting the app

The UI setting overrides the environment variable for that session.

