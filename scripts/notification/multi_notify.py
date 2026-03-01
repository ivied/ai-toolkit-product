#!/usr/bin/env python3
"""
Multi-Channel Notifier — Send alerts to multiple platforms at once.

Unified interface for Slack, Discord, Telegram, and email notifications.
Configure channels once, then notify everywhere with one command.

Usage:
    python multi_notify.py --message "Deploy complete!" --channels slack,telegram
    python multi_notify.py --message "Server alert!" --all --priority high
    python multi_notify.py --config notify.json --message "Custom alert"

Configuration (notify.json or environment variables):
    SLACK_WEBHOOK    — Slack webhook URL
    DISCORD_WEBHOOK  — Discord webhook URL
    TELEGRAM_TOKEN   — Telegram bot token
    TELEGRAM_CHAT_ID — Telegram chat ID
    SMTP_USER        — Email sender
    SMTP_PASSWORD    — Email password
    ALERT_EMAIL      — Email recipient

Requirements:
    pip install requests
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)

PRIORITY_EMOJIS = {"low": "ℹ️", "medium": "⚠️", "high": "🔴", "critical": "🚨"}


def send_slack(message: str, webhook_url: str, priority: str = "medium") -> dict:
    emoji = PRIORITY_EMOJIS.get(priority, "")
    payload = {"text": f"{emoji} {message}", "unfurl_links": False}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return {"channel": "slack", "ok": resp.status_code == 200}
    except Exception as e:
        return {"channel": "slack", "ok": False, "error": str(e)}


def send_discord(message: str, webhook_url: str, priority: str = "medium") -> dict:
    emoji = PRIORITY_EMOJIS.get(priority, "")
    colors = {"low": 0x3498DB, "medium": 0xF39C12, "high": 0xE74C3C, "critical": 0xFF0000}
    payload = {
        "embeds": [{
            "description": f"{emoji} {message}",
            "color": colors.get(priority, 0xF39C12),
            "timestamp": datetime.utcnow().isoformat(),
        }]
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return {"channel": "discord", "ok": resp.status_code in (200, 204)}
    except Exception as e:
        return {"channel": "discord", "ok": False, "error": str(e)}


def send_telegram(message: str, token: str, chat_id: str, priority: str = "medium") -> dict:
    emoji = PRIORITY_EMOJIS.get(priority, "")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": f"{emoji} {message}", "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return {"channel": "telegram", "ok": resp.json().get("ok", False)}
    except Exception as e:
        return {"channel": "telegram", "ok": False, "error": str(e)}


def send_email_simple(message: str, subject: str = "Alert Notification",
                      smtp_user: str = None, smtp_pass: str = None,
                      to_email: str = None) -> dict:
    """Send simple email alert via SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    
    user = smtp_user or os.getenv("SMTP_USER", "")
    password = smtp_pass or os.getenv("SMTP_PASSWORD", "")
    to = to_email or os.getenv("ALERT_EMAIL", "")
    
    if not all([user, password, to]):
        return {"channel": "email", "ok": False, "error": "Missing SMTP_USER/SMTP_PASSWORD/ALERT_EMAIL"}
    
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        
        with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587"))) as s:
            s.starttls()
            s.login(user, password)
            s.sendmail(user, [to], msg.as_string())
        
        return {"channel": "email", "ok": True}
    except Exception as e:
        return {"channel": "email", "ok": False, "error": str(e)}


def notify(message: str, channels: list[str], priority: str = "medium",
           config: dict = None) -> list[dict]:
    """Send notification to multiple channels."""
    config = config or {}
    results = []
    
    for channel in channels:
        if channel == "slack":
            url = config.get("slack_webhook") or os.getenv("SLACK_WEBHOOK", "")
            if url:
                results.append(send_slack(message, url, priority))
            else:
                results.append({"channel": "slack", "ok": False, "error": "No webhook URL"})
        
        elif channel == "discord":
            url = config.get("discord_webhook") or os.getenv("DISCORD_WEBHOOK", "")
            if url:
                results.append(send_discord(message, url, priority))
            else:
                results.append({"channel": "discord", "ok": False, "error": "No webhook URL"})
        
        elif channel == "telegram":
            token = config.get("telegram_token") or os.getenv("TELEGRAM_TOKEN", "")
            chat_id = config.get("telegram_chat_id") or os.getenv("TELEGRAM_CHAT_ID", "")
            if token and chat_id:
                results.append(send_telegram(message, token, chat_id, priority))
            else:
                results.append({"channel": "telegram", "ok": False, "error": "No token/chat_id"})
        
        elif channel == "email":
            results.append(send_email_simple(message))
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Multi-channel notification sender")
    parser.add_argument("--message", "-m", required=True, help="Message to send")
    parser.add_argument("--channels", "-c", default="slack", help="Channels (comma-separated)")
    parser.add_argument("--all", action="store_true", help="Send to all configured channels")
    parser.add_argument("--priority", choices=PRIORITY_EMOJIS.keys(), default="medium")
    parser.add_argument("--config", help="JSON config file")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    
    config = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    
    channels = ["slack", "discord", "telegram", "email"] if args.all else args.channels.split(",")
    results = notify(args.message, channels, args.priority, config)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            icon = "✅" if r["ok"] else "❌"
            extra = f" — {r.get('error', '')}" if not r["ok"] else ""
            print(f"  {icon} {r['channel']}{extra}")


if __name__ == "__main__":
    main()
