#!/usr/bin/env python3
"""
Slack Webhook Notifier
======================
Send rich notifications to Slack via incoming webhooks.
Supports formatted messages, attachments, and blocks.

Usage:
    python slack_webhook.py "Deployment complete ✅"
    python slack_webhook.py --title "Alert" --color danger "Server CPU at 95%"
    echo "Build failed" | python slack_webhook.py --title "CI/CD"
    python slack_webhook.py --json '{"blocks": [...]}'

Environment:
    SLACK_WEBHOOK_URL — Incoming webhook URL from Slack
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

COLORS = {
    "good": "#36a64f",
    "warning": "#daa520",
    "danger": "#ff0000",
    "info": "#2196F3",
    "purple": "#9c27b0",
}


def build_payload(text: str, title: str | None = None, color: str | None = None,
                  fields: list[tuple[str, str]] | None = None, footer: str | None = None) -> dict:
    """Build a Slack message payload with optional formatting."""

    if not title and not color and not fields:
        return {"text": text}

    attachment = {"text": text, "ts": int(datetime.now().timestamp())}

    if title:
        attachment["title"] = title
    if color:
        attachment["color"] = COLORS.get(color, color)  # Named or hex
    if fields:
        attachment["fields"] = [
            {"title": k, "value": v, "short": len(v) < 30} for k, v in fields
        ]
    if footer:
        attachment["footer"] = footer

    return {"attachments": [attachment]}


def build_blocks_payload(header: str, sections: list[str], 
                          actions: list[dict] | None = None) -> dict:
    """Build a Slack Block Kit message."""
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": header}},
        {"type": "divider"},
    ]

    for section in sections:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": section},
        })

    if actions:
        blocks.append({
            "type": "actions",
            "elements": actions,
        })

    return {"blocks": blocks}


def send(webhook_url: str, payload: dict) -> bool:
    """Send payload to Slack webhook."""
    with httpx.Client(timeout=10) as client:
        resp = client.post(webhook_url, json=payload)
        if resp.status_code == 200 and resp.text == "ok":
            return True
        print(f"Slack error ({resp.status_code}): {resp.text}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Send Slack notifications via webhook")
    parser.add_argument("message", nargs="?", help="Message text (or pipe via stdin)")
    parser.add_argument("--title", help="Message title")
    parser.add_argument("--color", help="Sidebar color: good/warning/danger/info or hex")
    parser.add_argument("--field", nargs=2, action="append", metavar=("KEY", "VALUE"),
                        help="Add a field (repeatable)")
    parser.add_argument("--footer", help="Footer text")
    parser.add_argument("--json", dest="raw_json", help="Send raw JSON payload")
    parser.add_argument("--webhook", help="Override webhook URL")
    args = parser.parse_args()

    webhook_url = args.webhook or os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Error: Set SLACK_WEBHOOK_URL or use --webhook")
        sys.exit(1)

    # Get message
    if args.raw_json:
        payload = json.loads(args.raw_json)
    else:
        message = args.message
        if not message:
            if not sys.stdin.isatty():
                message = sys.stdin.read().strip()
            else:
                print("Provide a message or pipe via stdin")
                sys.exit(1)

        payload = build_payload(
            text=message,
            title=args.title,
            color=args.color,
            fields=[(k, v) for k, v in args.field] if args.field else None,
            footer=args.footer,
        )

    if send(webhook_url, payload):
        print("✅ Sent to Slack")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
