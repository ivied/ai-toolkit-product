#!/usr/bin/env python3
"""
Minimal Slack Bot Template — Respond to messages and slash commands.

Setup:
1. Create app at api.slack.com/apps
2. Enable Socket Mode + Event Subscriptions
3. Subscribe to: message.im, app_mention
4. Install to workspace
5. Set env vars: SLACK_BOT_TOKEN, SLACK_APP_TOKEN

Requirements:
    pip install slack-bolt
"""

import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(token=os.environ["SLACK_BOT_TOKEN"])


@app.event("app_mention")
def handle_mention(event, say):
    """Respond when mentioned in a channel."""
    user = event["user"]
    text = event.get("text", "").lower()
    
    if "help" in text:
        say(f"<@{user}> Here's what I can do:\n• `@bot help` — Show this help\n• `@bot status` — Check system status\n• `@bot summarize <url>` — Summarize a webpage")
    elif "status" in text:
        say(f"<@{user}> ✅ All systems operational!")
    else:
        say(f"Hey <@{user}>! Try `@bot help` to see what I can do.")


@app.event("message")
def handle_dm(event, say):
    """Handle direct messages."""
    if event.get("channel_type") == "im":
        text = event.get("text", "")
        say(f"You said: {text}\n\nI'm a simple bot template. Customize me in `app.py`!")


@app.command("/toolkit")
def handle_command(ack, respond, command):
    """Handle /toolkit slash command."""
    ack()
    action = command.get("text", "help").strip()
    
    if action == "help":
        respond("Available commands:\n• `/toolkit help` — Show help\n• `/toolkit status` — Check status\n• `/toolkit version` — Show version")
    elif action == "status":
        respond("✅ Bot is running!")
    elif action == "version":
        respond("AI Toolkit Bot v1.0")
    else:
        respond(f"Unknown command: {action}. Try `/toolkit help`")


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("⚡ Slack bot started!")
    handler.start()
