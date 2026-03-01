# Getting API Keys

Quick guide to getting API keys for all services used in this toolkit.

## OpenAI

1. Go to [platform.openai.com](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to **API Keys** in the left sidebar
4. Click **Create new secret key**
5. Copy the key (starts with `sk-`)

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Free tier:** $5 credit for new accounts. GPT-4o-mini is cheapest (~$0.15/1M tokens).

## Anthropic (Claude)

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up → **API Keys** section
3. Create a key

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

## Slack (Webhooks)

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. **Create New App** → From scratch
3. **Incoming Webhooks** → Activate → Add to channel
4. Copy the webhook URL

```bash
export SLACK_WEBHOOK="https://hooks.slack.com/services/T.../B.../xxx"
```

## Discord (Webhooks)

1. Open Discord → Server Settings → Integrations
2. **Webhooks** → New Webhook
3. Copy Webhook URL

```bash
export DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."
```

## Telegram (Bot)

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow prompts
3. Copy the bot token

```bash
export TELEGRAM_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="your-chat-id"  # Get from @userinfobot
```

## Gmail (App Password for SMTP)

1. Enable 2-Factor Authentication on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Generate an App Password for "Mail"

```bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your@gmail.com"
export SMTP_PASSWORD="your-app-password"
```

## GitHub (Personal Access Token)

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. **Generate new token** (classic or fine-grained)
3. Select scopes: `repo`, `read:org`

```bash
export GITHUB_TOKEN="ghp_..."
```

## Tips

- **Never commit API keys** to git — use `.env` files
- **Rotate keys** regularly (every 90 days)
- **Use environment variables** — all scripts in this toolkit read from env
- **Start with free tiers** — most services offer generous free usage
- Create a `.env` file in your project root:

```bash
# .env
OPENAI_API_KEY=sk-...
SLACK_WEBHOOK=https://hooks.slack.com/...
```

Load it with: `source .env` or use `python-dotenv` in Python.
