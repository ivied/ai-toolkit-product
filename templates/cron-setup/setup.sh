#!/bin/bash
# Cron Setup Template — Quick setup for common monitoring cron jobs.
#
# Usage: ./setup.sh [install|show|remove]

set -euo pipefail

TOOLKIT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="$TOOLKIT_DIR/venv"
PYTHON="$VENV/bin/python"

# Cron job definitions (customize these!)
CRON_JOBS=(
    # "schedule|name|command"
    "0 */6 * * *|news-digest|$PYTHON $TOOLKIT_DIR/scripts/web-scraping/news_aggregator.py > ~/news-digest.md"
    "*/30 * * * *|health-check|$PYTHON $TOOLKIT_DIR/scripts/devops/health_check.py https://example.com"
    "0 2 * * *|backup|$PYTHON $TOOLKIT_DIR/scripts/devops/backup_rotation.py --source ~/data --dest ~/backups --compress gz"
    "0 9 * * 1|weekly-report|$PYTHON $TOOLKIT_DIR/scripts/data-processing/report_generator.py ~/data/metrics.csv --title 'Weekly Report'"
)

MARKER="# AI-TOOLKIT-CRON"

show_jobs() {
    echo "📋 Configured cron jobs:"
    for job in "${CRON_JOBS[@]}"; do
        IFS='|' read -r schedule name cmd <<< "$job"
        echo "  ⏰ $name: $schedule"
        echo "     $cmd"
    done
}

install_jobs() {
    echo "📥 Installing cron jobs..."
    
    # Check venv exists
    if [ ! -f "$PYTHON" ]; then
        echo "❌ Virtual environment not found at $VENV"
        echo "   Run: python3 -m venv $VENV && $VENV/bin/pip install -r $TOOLKIT_DIR/requirements.txt"
        exit 1
    fi
    
    # Get current crontab (ignore error if empty)
    CURRENT=$(crontab -l 2>/dev/null || true)
    
    # Remove old toolkit entries
    CLEANED=$(echo "$CURRENT" | grep -v "$MARKER" || true)
    
    # Add new entries
    NEW="$CLEANED"
    for job in "${CRON_JOBS[@]}"; do
        IFS='|' read -r schedule name cmd <<< "$job"
        NEW="$NEW
$schedule $cmd $MARKER $name"
    done
    
    echo "$NEW" | crontab -
    echo "✅ Installed ${#CRON_JOBS[@]} cron jobs"
    show_jobs
}

remove_jobs() {
    echo "🗑️  Removing AI Toolkit cron jobs..."
    CURRENT=$(crontab -l 2>/dev/null || true)
    CLEANED=$(echo "$CURRENT" | grep -v "$MARKER" || true)
    echo "$CLEANED" | crontab -
    echo "✅ Removed"
}

case "${1:-show}" in
    install) install_jobs ;;
    show)    show_jobs ;;
    remove)  remove_jobs ;;
    *)       echo "Usage: $0 [install|show|remove]" ;;
esac
