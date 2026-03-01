#!/usr/bin/env python3
"""
Discord Webhook Sender — Send rich messages to Discord via webhooks.

Supports plain text, embeds, file attachments, and @mentions.

Usage:
    python discord_webhook.py --url $WEBHOOK_URL --message "Deploy complete! ✅"
    python discord_webhook.py --url $WEBHOOK_URL --title "Alert" --description "CPU at 95%" --color red
    python discord_webhook.py --url $WEBHOOK_URL --file report.txt --message "Daily report"

Requirements:
    pip install requests
"""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)

COLORS = {
    "red": 0xFF0000, "green": 0x00FF00, "blue": 0x0000FF,
    "yellow": 0xFFFF00, "orange": 0xFF8C00, "purple": 0x800080,
    "cyan": 0x00FFFF, "white": 0xFFFFFF, "gray": 0x808080,
}


def send_message(webhook_url: str, message: str = None, username: str = None,
                 avatar_url: str = None, embed: dict = None, file_path: str = None) -> dict:
    """Send a message to Discord webhook."""
    payload = {}
    if message:
        payload["content"] = message
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url
    if embed:
        payload["embeds"] = [embed]
    
    if file_path:
        with open(file_path, "rb") as f:
            resp = requests.post(
                webhook_url,
                data={"payload_json": json.dumps(payload)} if payload else None,
                files={"file": (os.path.basename(file_path), f)},
            )
    else:
        resp = requests.post(webhook_url, json=payload)
    
    return {
        "status": resp.status_code,
        "ok": resp.status_code in (200, 204),
        "response": resp.text[:200] if resp.text else "",
    }


def build_embed(title: str = None, description: str = None, color: str = "blue",
                url: str = None, fields: list = None, footer: str = None,
                thumbnail: str = None, image: str = None) -> dict:
    """Build a Discord embed object."""
    embed = {}
    if title: embed["title"] = title
    if description: embed["description"] = description
    if url: embed["url"] = url
    if color:
        embed["color"] = COLORS.get(color.lower(), int(color, 16) if color.startswith("0x") else COLORS["blue"])
    if fields:
        embed["fields"] = fields
    if footer:
        embed["footer"] = {"text": footer}
    if thumbnail:
        embed["thumbnail"] = {"url": thumbnail}
    if image:
        embed["image"] = {"url": image}
    embed["timestamp"] = __import__("datetime").datetime.utcnow().isoformat()
    return embed


def main():
    parser = argparse.ArgumentParser(description="Send Discord webhook messages")
    parser.add_argument("--url", required=True, help="Webhook URL (or DISCORD_WEBHOOK env)")
    parser.add_argument("--message", "-m", help="Plain text message")
    parser.add_argument("--username", help="Override bot username")
    parser.add_argument("--avatar", help="Override bot avatar URL")
    parser.add_argument("--file", help="File to attach")
    
    # Embed options
    parser.add_argument("--title", help="Embed title")
    parser.add_argument("--description", help="Embed description")
    parser.add_argument("--color", default="blue", help="Embed color (name or hex)")
    parser.add_argument("--embed-url", help="Embed URL")
    parser.add_argument("--footer", help="Embed footer text")
    parser.add_argument("--thumbnail", help="Embed thumbnail URL")
    parser.add_argument("--image", help="Embed image URL")
    parser.add_argument("--field", action="append", help="Field as 'name:value' or 'name:value:inline'")
    args = parser.parse_args()
    
    webhook_url = args.url or os.getenv("DISCORD_WEBHOOK")
    if not webhook_url:
        parser.error("Provide --url or set DISCORD_WEBHOOK env var")
    
    embed = None
    if any([args.title, args.description, args.field]):
        fields = []
        if args.field:
            for f in args.field:
                parts = f.split(":", 2)
                field = {"name": parts[0], "value": parts[1] if len(parts) > 1 else ""}
                if len(parts) > 2 and parts[2].lower() in ("true", "1", "inline"):
                    field["inline"] = True
                fields.append(field)
        
        embed = build_embed(
            title=args.title, description=args.description,
            color=args.color, url=args.embed_url, fields=fields or None,
            footer=args.footer, thumbnail=args.thumbnail, image=args.image,
        )
    
    result = send_message(
        webhook_url, message=args.message, username=args.username,
        avatar_url=args.avatar, embed=embed, file_path=args.file,
    )
    
    if result["ok"]:
        print("✅ Message sent!")
    else:
        print(f"❌ Failed ({result['status']}): {result['response']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
