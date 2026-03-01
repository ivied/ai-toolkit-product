# ⚡ Quick Start Guide

Get running in 5 minutes.

## Prerequisites

- **Python 3.10+** (check: `python3 --version`)
- **pip** (comes with Python)

## Setup

```bash
# 1. Install the main dependency (most scripts only need this)
pip install httpx

# 2. For AI scripts, also install:
pip install sentence-transformers  # for local embeddings (chat_with_docs)

# 3. For specific scripts:
pip install selectolax     # price_monitor
pip install weasyprint     # markdown_to_pdf (PDF output)
pip install PyMuPDF        # batch_summarize (PDF input)
```

## API Keys (only for AI scripts)

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Or Anthropic (Claude)
export ANTHROPIC_API_KEY="sk-ant-..."
```

Get keys:
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys

## Try It!

### No API key needed:
```bash
# Organize messy downloads folder
python scripts/productivity/file_organizer.py ~/Downloads --mode type --dry-run

# Analyze a CSV file
python scripts/data-processing/csv_toolkit.py info your_data.csv

# Monitor a product price
python scripts/web-scraping/price_monitor.py add "https://example.com" ".price" --name "Widget"
```

### With OpenAI key:
```bash
# Summarize all documents in a folder
python scripts/ai-integration/batch_summarize.py ./documents/

# Chat with your docs (RAG)
python scripts/ai-integration/chat_with_docs.py ./docs/

# Extract structured data from text
echo "John Smith, john@acme.com, CEO at Acme Inc" | \
  python scripts/ai-integration/structured_extractor.py --schema contact
```

### Notifications:
```bash
# Send a Slack message
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
python scripts/notification/slack_webhook.py "Deployment complete ✅"

# Run a Telegram bot
export TELEGRAM_BOT_TOKEN="123456:ABC..."
python scripts/notification/telegram_bot.py
```

## Next Steps

- Browse `scripts/` — each script has a detailed header with usage instructions
- Check `prompts/` — copy-paste AI prompts organized by category  
- Read `guides/` — detailed setup guides for specific tools
