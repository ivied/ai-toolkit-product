# Deployment Guide

How to deploy scripts from this toolkit on various platforms.

## Local (Cron Jobs)

The simplest deployment — run scripts on a schedule using cron.

```bash
# Edit crontab
crontab -e

# Run price monitor every hour
0 * * * * cd /path/to/toolkit && python scripts/web-scraping/price_monitor.py >> /var/log/price-monitor.log 2>&1

# Run backup daily at 2 AM
0 2 * * * cd /path/to/toolkit && python scripts/devops/backup_rotation.py --source /data --dest /backups --compress gz

# Run news aggregator every 6 hours
0 */6 * * * cd /path/to/toolkit && python scripts/web-scraping/news_aggregator.py > ~/news-digest.md
```

**Tip:** Use the `cron_monitor.py` wrapper for failure alerts:
```bash
0 * * * * python scripts/notification/cron_monitor.py --name "price-check" --cmd "python scripts/web-scraping/price_monitor.py" --notify slack
```

## VPS (DigitalOcean, Linode, Hetzner)

### Setup

```bash
# SSH into your server
ssh user@your-server

# Clone the toolkit
git clone https://github.com/your-user/ai-toolkit-product.git
cd ai-toolkit-product

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
nano .env  # Fill in your keys

# Test
source .env && python scripts/devops/health_check.py
```

### Systemd Service (for long-running scripts)

```ini
# /etc/systemd/system/api-monitor.service
[Unit]
Description=API Monitor
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/ai-toolkit
Environment=PATH=/opt/ai-toolkit/venv/bin
EnvironmentFile=/opt/ai-toolkit/.env
ExecStart=/opt/ai-toolkit/venv/bin/python scripts/web-scraping/api_monitor.py --url https://api.example.com --interval 60
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable api-monitor
sudo systemctl start api-monitor
sudo journalctl -u api-monitor -f  # View logs
```

## Docker

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ scripts/
COPY .env .env

CMD ["python", "scripts/web-scraping/price_monitor.py"]
```

```bash
docker build -t my-monitor .
docker run -d --env-file .env --name monitor my-monitor
```

## GitHub Actions

Run scripts on a schedule using GitHub Actions — free for public repos.

```yaml
# .github/workflows/monitor.yml
name: Daily Monitor
on:
  schedule:
    - cron: '0 9 * * *'  # 9 AM UTC daily
  workflow_dispatch:  # Manual trigger

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python scripts/web-scraping/news_aggregator.py > digest.md
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      - run: python scripts/notification/slack_webhook.py --file digest.md
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
```

## Railway / Render / Fly.io

These platforms support Python apps with minimal config.

### Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Deploy
railway init
railway up
```

Add a `Procfile`:
```
worker: python scripts/web-scraping/api_monitor.py --interval 60
```

### Render

Create a `render.yaml`:
```yaml
services:
  - type: worker
    name: api-monitor
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python scripts/web-scraping/api_monitor.py --interval 60
    envVars:
      - key: OPENAI_API_KEY
        sync: false
```

## Tips

- **Always use virtual environments** — avoid system Python conflicts
- **Pin dependencies** — `pip freeze > requirements.txt`
- **Use `.env` files** — never hardcode secrets
- **Set up monitoring** — use `cron_monitor.py` or `health_check.py`
- **Log everything** — redirect output to files or use a logging service
- **Start simple** — cron on a $5 VPS handles most use cases
