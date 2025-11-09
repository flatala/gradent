# 🚀 ntfy.sh Integration - Setup & Testing Guide

## ✅ What I Just Implemented

### Backend (`notifications/autonomous.py`)
- ✅ Added `send_ntfy_notification()` function
- ✅ Updated `send_tool_completion_notification()` to support ntfy
- ✅ Updated `send_execution_summary()` to support ntfy
- ✅ Supports emoji tags, priorities, and titles

### Frontend (`AutonomousMode.tsx`)
- ✅ Added ntfy topic input field
- ✅ Added visual instructions for subscribing
- ✅ Saves ntfy_topic in configuration
- ✅ Beautiful UI card with step-by-step guide

### Types
- ✅ Updated `AutonomousConfigPayload` to include `ntfy_topic`
- ✅ Updated `AutonomousConfigResponse`

## 🧪 How to Test It Right Now (2 minutes)

### Option 1: Test Script (Quickest)

1. **Run the test script:**
   ```bash
   cd /Users/alex.zheng/hackathon/gradent
   python3 test_ntfy.py
   ```

2. **Open the link shown** (example: https://ntfy.sh/gradent-ai-test-123)

3. **Click "Subscribe" in your browser**

4. **Wait 3 seconds** - you'll see the notification appear!

### Option 2: Test from Browser (No Code)

1. **Open in browser:** https://ntfy.sh/gradent-ai-demo

2. **Click "Subscribe"** button

3. **Send a test notification:**
   ```bash
   curl -d "Hello from GradEnt AI! 🤖" https://ntfy.sh/gradent-ai-demo
   ```

4. **See the notification** appear in your browser instantly!

### Option 3: Test on Mobile (Most Impressive)

1. **Download ntfy app:**
   - iOS: https://apps.apple.com/app/ntfy/id1625396347
   - Android: https://play.google.com/store/apps/details?id=io.heckel.ntfy

2. **Open app and tap "+"**

3. **Enter topic:** `gradent-ai-demo`

4. **Send notification:**
   ```bash
   curl -d "Test from mobile! 📱" https://ntfy.sh/gradent-ai-demo
   ```

5. **Get push notification on your phone!**

## 📱 How Users Will Use It

### Step 1: Configure in UI
1. Go to **Autonomous Mode** tab
2. Scroll to **"ntfy Mobile Notifications"** card
3. Enter a custom topic (default: `gradent-ai`)
4. Click **"Save Configuration"**

### Step 2: Subscribe
Users can subscribe in 3 ways:

**A. Browser (Desktop)**
- Visit: https://ntfy.sh/gradent-ai
- Click "Subscribe"
- Get desktop notifications

**B. Mobile App**
- Download ntfy app
- Tap "+" → Add topic
- Enter: `gradent-ai`
- Get push notifications

**C. Email**
- In ntfy app: Settings → Email
- Configure forwarding
- Get notifications via email

### Step 3: Run Autonomous Mode
1. Click **"Run Now"** or enable scheduled execution
2. Notifications appear as tasks complete:
   - 📅 "Schedule Meeting completed!"
   - 💡 "Generated 5 study suggestions!"
   - 📊 "Assignment assessed!"

## 🎪 Hackathon Demo Script

> **Presenter:** "Let me show you how notifications work. I'm going to open ntfy.sh on my phone..."
> 
> *Opens ntfy app, shows subscribing to topic*
> 
> **Presenter:** "Now watch - I'll click 'Run Now' in autonomous mode..."
> 
> *Clicks button*
> 
> **Presenter:** "And there it is! Real-time notification on my phone. No signup, no app to publish, just works."
> 
> *Phone buzzes with notification*
> 
> **Judges:** 😮 "That's pretty cool!"
> 
> **Presenter:** "And it works on desktop, email, Discord - any channel the user wants. All from one simple setup."

## 🔧 What Still Needs to Be Done

The frontend is 100% ready. You just need to add the backend endpoints:

### 1. Add to `app/main.py` Pydantic Models:

```python
class AutonomousConfigPayload(BaseModel):
    enabled: bool
    frequency: Literal["15min", "30min", "1hour", "3hours", "6hours", "12hours", "24hours"]
    discord_webhook: Optional[str] = None
    ntfy_topic: Optional[str] = Field(default="gradent-ai")  # NEW

class AutonomousConfigResponse(AutonomousConfigPayload):
    last_execution: Optional[str] = None
    next_execution: Optional[str] = None
```

### 2. Add Config Storage:

```python
AUTONOMOUS_CONFIG = {
    "enabled": False,
    "frequency": "1hour",
    "discord_webhook": None,
    "ntfy_topic": "gradent-ai",  # NEW
    "last_execution": None,
    "next_execution": None,
}
```

### 3. Add the 4 API Endpoints:

```python
from notifications.autonomous import (
    send_discord_embed,
    send_tool_completion_notification,
    send_execution_summary,
    send_ntfy_notification,  # NEW
)

@app.get("/api/autonomous/config", response_model=AutonomousConfigResponse)
async def get_autonomous_config():
    return AutonomousConfigResponse(**AUTONOMOUS_CONFIG)

@app.put("/api/autonomous/config", response_model=SimpleStatusResponse)
async def update_autonomous_config(payload: AutonomousConfigPayload):
    global AUTONOMOUS_CONFIG
    AUTONOMOUS_CONFIG["enabled"] = payload.enabled
    AUTONOMOUS_CONFIG["frequency"] = payload.frequency
    AUTONOMOUS_CONFIG["discord_webhook"] = payload.discord_webhook
    AUTONOMOUS_CONFIG["ntfy_topic"] = payload.ntfy_topic  # NEW
    return SimpleStatusResponse(status="ok", message="Configuration updated")

@app.post("/api/autonomous/execute", response_model=SimpleStatusResponse)
async def trigger_autonomous_execution():
    # TODO: Trigger executor agent
    # For now, just send a test notification
    ntfy_topic = AUTONOMOUS_CONFIG.get("ntfy_topic")
    if ntfy_topic:
        await send_ntfy_notification(
            "Autonomous agent execution started! 🤖",
            topic=ntfy_topic,
            title="🤖 Autonomous Agent Started",
            priority=4
        )
    return SimpleStatusResponse(status="ok", message="Execution started")

@app.post("/api/autonomous/test-webhook", response_model=SimpleStatusResponse)
async def test_discord_webhook(payload: TestWebhookPayload):
    success = await send_discord_embed(
        payload.webhook_url,
        "🧪 Test Notification",
        "This is a test message from GradEnt AI!",
        5814783
    )
    if success:
        return SimpleStatusResponse(status="ok", message="Test notification sent")
    else:
        raise HTTPException(status_code=400, detail="Failed to send notification")
```

### 4. Update Tool Callback:

```python
class AutonomousToolCallTracker(BaseCallbackHandler):
    def __init__(self, discord_webhook: Optional[str] = None, ntfy_topic: Optional[str] = None):
        self.discord_webhook = discord_webhook
        self.ntfy_topic = ntfy_topic  # NEW
        # ... rest of init
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        # ... existing code ...
        
        # Send notifications
        asyncio.create_task(
            send_tool_completion_notification(
                self.discord_webhook or "",
                last_tool["tool_type"],
                last_tool["tool_name"],
                last_tool["result"],
                ntfy_topic=self.ntfy_topic  # NEW
            )
        )
```

## 📦 Dependencies

ntfy uses httpx which should already be in your dependencies. If not:

```bash
cd /Users/alex.zheng/hackathon/gradent
poetry add httpx
```

## ✨ Benefits

### Why ntfy is Perfect for Hackathon:

1. **Zero Setup** - No API keys, no accounts
2. **Works Instantly** - Test in 30 seconds
3. **Multi-Channel** - Web, mobile, email from one API
4. **Visual Impact** - Push notifications impress judges
5. **Free** - Unlimited notifications
6. **Open Source** - Can self-host if needed

### Demo Advantages:

- **"It just works"** - Most impressive demo feature
- **Mobile-first** - Shows modern thinking
- **User-friendly** - No complex setup for users
- **Scalable** - Works for 1 or 1000 users

## 🎯 Next Steps

1. **Test ntfy right now:**
   ```bash
   python3 test_ntfy.py
   ```

2. **Add backend endpoints** (see code above)

3. **Test full flow**:
   - Configure ntfy topic in UI
   - Subscribe on mobile
   - Click "Run Now"
   - Get notifications!

4. **Prepare demo**:
   - Have ntfy app ready on phone
   - Subscribe to demo topic before judges arrive
   - Show live notifications during presentation

## 🚀 You're Ready!

The ntfy integration is complete on the frontend. Just add the backend endpoints and you'll have a fully working multi-channel notification system!

Want to test it right now? Run: `python3 test_ntfy.py`

