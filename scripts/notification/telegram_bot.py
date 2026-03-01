#!/usr/bin/env python3
"""
Telegram Bot Template
=====================
A clean, extensible Telegram bot with command handling, inline keyboards,
and webhook support. Ready to customize for your use case.

Usage:
    python telegram_bot.py                    # Long polling mode
    python telegram_bot.py --webhook https://yourdomain.com/webhook

Environment:
    TELEGRAM_BOT_TOKEN — Bot token from @BotFather

Requirements:
    pip install httpx
"""

import argparse
import asyncio
import json
import os
import signal
import sys
from dataclasses import dataclass
from typing import Any, Callable

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


@dataclass
class Update:
    """Parsed Telegram update."""
    update_id: int
    message: dict | None = None
    callback_query: dict | None = None

    @property
    def chat_id(self) -> int | None:
        if self.message:
            return self.message["chat"]["id"]
        if self.callback_query:
            return self.callback_query["message"]["chat"]["id"]
        return None

    @property
    def text(self) -> str | None:
        return self.message.get("text") if self.message else None

    @property
    def user(self) -> dict | None:
        if self.message:
            return self.message.get("from")
        if self.callback_query:
            return self.callback_query.get("from")
        return None

    @property
    def username(self) -> str:
        u = self.user
        return u.get("username", u.get("first_name", "unknown")) if u else "unknown"


class TelegramBot:
    """Simple async Telegram bot."""

    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.client = httpx.AsyncClient(timeout=30)
        self.commands: dict[str, Callable] = {}
        self.callback_handlers: dict[str, Callable] = {}
        self._running = True

    def command(self, name: str):
        """Decorator to register a command handler."""
        def decorator(func):
            self.commands[name] = func
            return func
        return decorator

    def callback(self, prefix: str):
        """Decorator to register a callback query handler."""
        def decorator(func):
            self.callback_handlers[prefix] = func
            return func
        return decorator

    async def api(self, method: str, **kwargs) -> dict:
        """Call Telegram Bot API."""
        resp = await self.client.post(f"{self.base_url}/{method}", json=kwargs)
        data = resp.json()
        if not data.get("ok"):
            raise Exception(f"Telegram API error: {data}")
        return data.get("result", {})

    async def send(self, chat_id: int, text: str, **kwargs) -> dict:
        """Send a text message."""
        return await self.api("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", **kwargs)

    async def send_buttons(self, chat_id: int, text: str, buttons: list[list[dict]]) -> dict:
        """Send message with inline keyboard buttons."""
        keyboard = {"inline_keyboard": buttons}
        return await self.send(chat_id, text, reply_markup=keyboard)

    async def answer_callback(self, callback_query_id: str, text: str = "") -> dict:
        return await self.api("answerCallbackQuery", callback_query_id=callback_query_id, text=text)

    async def handle_update(self, update_data: dict):
        """Process a single update."""
        update = Update(
            update_id=update_data["update_id"],
            message=update_data.get("message"),
            callback_query=update_data.get("callback_query"),
        )

        # Handle callback queries
        if update.callback_query:
            data = update.callback_query.get("data", "")
            await self.answer_callback(update.callback_query["id"])
            for prefix, handler in self.callback_handlers.items():
                if data.startswith(prefix):
                    await handler(update, data)
                    return

        # Handle commands
        if update.text and update.text.startswith("/"):
            cmd = update.text.split()[0].lstrip("/").split("@")[0]
            if cmd in self.commands:
                await self.commands[cmd](update)
                return

    async def poll(self):
        """Long polling loop."""
        offset = 0
        print("🤖 Bot running (long polling)... Press Ctrl+C to stop")

        while self._running:
            try:
                updates = await self.api("getUpdates", offset=offset, timeout=30)
                for u in updates:
                    offset = u["update_id"] + 1
                    try:
                        await self.handle_update(u)
                    except Exception as e:
                        print(f"Error handling update: {e}")
            except httpx.ReadTimeout:
                continue
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(5)

    async def close(self):
        self._running = False
        await self.client.aclose()


# ============================================================
# Example bot — customize below!
# ============================================================

bot = TelegramBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""))


@bot.command("start")
async def cmd_start(update: Update):
    await bot.send_buttons(
        update.chat_id,
        f"👋 Hello <b>{update.username}</b>!\n\nI'm your bot. What would you like?",
        [
            [
                {"text": "📊 Status", "callback_data": "action:status"},
                {"text": "ℹ️ Help", "callback_data": "action:help"},
            ],
            [
                {"text": "⚙️ Settings", "callback_data": "action:settings"},
            ],
        ],
    )


@bot.command("help")
async def cmd_help(update: Update):
    await bot.send(
        update.chat_id,
        "📖 <b>Commands</b>\n\n"
        "/start — Main menu\n"
        "/help — This message\n"
        "/echo [text] — Echo back\n"
        "/time — Current time\n\n"
        "💡 Customize this bot in the source code!",
    )


@bot.command("echo")
async def cmd_echo(update: Update):
    text = update.text.replace("/echo", "", 1).strip()
    await bot.send(update.chat_id, text or "Usage: /echo <text>")


@bot.command("time")
async def cmd_time(update: Update):
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await bot.send(update.chat_id, f"🕐 {now}")


@bot.callback("action:")
async def handle_action(update: Update, data: str):
    action = data.split(":")[1]
    messages = {
        "status": "✅ Bot is running smoothly!",
        "help": "Use /help for available commands",
        "settings": "⚙️ Settings coming soon!",
    }
    await bot.send(update.chat_id, messages.get(action, f"Unknown action: {action}"))


async def main():
    parser = argparse.ArgumentParser(description="Telegram Bot")
    parser.add_argument("--webhook", help="Webhook URL (default: long polling)")
    args = parser.parse_args()

    if not bot.token:
        print("Error: Set TELEGRAM_BOT_TOKEN environment variable")
        sys.exit(1)

    # Get bot info
    me = await bot.api("getMe")
    print(f"Bot: @{me.get('username', 'unknown')}")

    if args.webhook:
        await bot.api("setWebhook", url=args.webhook)
        print(f"Webhook set to {args.webhook}")
        # You'd run a web server here to receive webhook POSTs
    else:
        await bot.api("deleteWebhook")
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(bot.close()))
        await bot.poll()

    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
