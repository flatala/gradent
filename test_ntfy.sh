#!/bin/bash
# Quick test for ntfy.sh notifications

echo "🧪 Testing ntfy.sh notification..."
echo "============================================================"
echo ""
echo "📱 Subscribe to receive this notification:"
echo "   Web: https://ntfy.sh/gradent-ai-test-123"
echo "   Mobile: Open ntfy app and add topic 'gradent-ai-test-123'"
echo ""
echo "⏳ Sending test notification..."
echo "============================================================"
echo ""

# Send notification
curl -H "Title: ✅ Test Notification" \
     -H "Priority: 5" \
     -H "Tags: tada,robot,white_check_mark" \
     -d "🎉 Success! Your ntfy integration is working!

This is a test from GradEnt AI." \
     https://ntfy.sh/gradent-ai-test-123

echo ""
echo ""
echo "============================================================"
echo "✅ Notification sent!"
echo ""
echo "📱 Check your subscription at: https://ntfy.sh/gradent-ai-test-123"
echo ""
echo "If you didn't see it:"
echo "1. Open https://ntfy.sh/gradent-ai-test-123 in your browser"
echo "2. Or download the ntfy mobile app and subscribe to 'gradent-ai-test-123'"
echo "============================================================"

