#!/usr/bin/env python3
"""
Minimal Telegram Bot Template — Handle commands and messages.

Setup:
1. Message @BotFather → /newbot → get token
2. Set TELEGRAM_TOKEN env var
3. Run this script

Requirements:
    pip install python-telegram-bot
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_TOKEN"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "👋 Hi! I'm your AI Toolkit bot.\n\n"
        "Commands:\n"
        "/help — Show available commands\n"
        "/status — Check bot status\n"
        "/echo <text> — Echo your message\n"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "Available commands:\n"
        "• /start — Welcome message\n"
        "• /help — This help\n"
        "• /status — Bot status\n"
        "• /echo <text> — Echo text back\n"
        "\nJust send me a message and I'll respond!"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    await update.message.reply_text("✅ Bot is running and healthy!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /echo command."""
    text = " ".join(context.args) if context.args else "Nothing to echo!"
    await update.message.reply_text(f"🔊 {text}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages."""
    text = update.message.text
    await update.message.reply_text(
        f"You said: {text}\n\n"
        "I'm a simple template bot. Customize me in `bot.py`!"
    )


def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("echo", echo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Telegram bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
