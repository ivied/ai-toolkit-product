#!/usr/bin/env python3
"""
Cron Job Monitor — Monitor cron/scheduled jobs and alert on failures.

Wraps any command and sends notifications on failure, timeout, or success.
Tracks execution history for reporting.

Usage:
    python cron_monitor.py --name "backup" --cmd "pg_dump mydb > backup.sql"
    python cron_monitor.py --name "sync" --cmd "./sync.sh" --timeout 300 --notify slack
    python cron_monitor.py report                    # Show job execution history
    python cron_monitor.py --name "test" --cmd "echo ok" --always-notify

Requirements:
    pip install requests  (for Slack/Discord notifications)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DATA = Path.home() / ".local" / "share" / "cron-monitor" / "history.json"


def load(): return json.loads(DATA.read_text()) if DATA.exists() else []
def save(h):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(h[-1000:], indent=2))


def send_notification(message, channel="stderr"):
    if channel == "stderr":
        print(message, file=sys.stderr)
    elif channel == "slack":
        url = os.getenv("SLACK_WEBHOOK", "")
        if url:
            import requests
            requests.post(url, json={"text": message}, timeout=10)
    elif channel == "discord":
        url = os.getenv("DISCORD_WEBHOOK", "")
        if url:
            import requests
            requests.post(url, json={"content": message}, timeout=10)
    elif channel == "telegram":
        token = os.getenv("TELEGRAM_TOKEN", "")
        chat = os.getenv("TELEGRAM_CHAT_ID", "")
        if token and chat:
            import requests
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                         json={"chat_id": chat, "text": message}, timeout=10)


def run_job(name, cmd, timeout=None, notify_channel="stderr", always_notify=False):
    start = time.time()
    start_dt = datetime.now()
    
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout,
        )
        elapsed = time.time() - start
        success = result.returncode == 0
        
        entry = {
            "name": name, "command": cmd,
            "start": start_dt.isoformat(),
            "duration_seconds": round(elapsed, 2),
            "exit_code": result.returncode,
            "success": success,
            "stdout_tail": result.stdout[-500:] if result.stdout else "",
            "stderr_tail": result.stderr[-500:] if result.stderr else "",
        }
        
        history = load()
        history.append(entry)
        save(history)
        
        if not success:
            msg = f"❌ Cron job '{name}' FAILED (exit {result.returncode}, {elapsed:.1f}s)\n"
            msg += f"Command: {cmd}\n"
            if result.stderr:
                msg += f"Error: {result.stderr[-200:]}"
            send_notification(msg, notify_channel)
        elif always_notify:
            send_notification(f"✅ Cron job '{name}' OK ({elapsed:.1f}s)", notify_channel)
        
        # Forward original output
        if result.stdout: sys.stdout.write(result.stdout)
        if result.stderr: sys.stderr.write(result.stderr)
        
        return result.returncode
        
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        entry = {
            "name": name, "command": cmd,
            "start": start_dt.isoformat(),
            "duration_seconds": round(elapsed, 2),
            "exit_code": -1, "success": False,
            "stderr_tail": f"TIMEOUT after {timeout}s",
        }
        history = load()
        history.append(entry)
        save(history)
        
        send_notification(f"⏰ Cron job '{name}' TIMEOUT after {timeout}s\nCommand: {cmd}", notify_channel)
        return 124


def show_report(name=None, limit=20):
    history = load()
    if name:
        history = [h for h in history if h.get("name") == name]
    
    if not history:
        print("No job history found.")
        return
    
    # Summary by job
    jobs = {}
    for h in history:
        n = h.get("name", "unknown")
        jobs.setdefault(n, {"total": 0, "success": 0, "fail": 0, "durations": []})
        jobs[n]["total"] += 1
        if h.get("success"): jobs[n]["success"] += 1
        else: jobs[n]["fail"] += 1
        jobs[n]["durations"].append(h.get("duration_seconds", 0))
    
    print("📊 Cron Job Report\n")
    for n, stats in sorted(jobs.items()):
        rate = stats["success"] / max(stats["total"], 1) * 100
        avg = sum(stats["durations"]) / len(stats["durations"])
        icon = "✅" if stats["fail"] == 0 else "⚠️" if rate > 80 else "❌"
        print(f"  {icon} {n}: {rate:.0f}% success ({stats['success']}/{stats['total']}), avg {avg:.1f}s")
    
    print(f"\nRecent ({min(limit, len(history))} entries):")
    for h in history[-limit:]:
        icon = "✅" if h.get("success") else "❌"
        print(f"  {icon} [{h.get('start', '')[:16]}] {h.get('name', '?')} — {h.get('duration_seconds', 0):.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Monitor cron/scheduled jobs")
    parser.add_argument("command", nargs="?", help="Use 'report' for history")
    parser.add_argument("--name", help="Job name")
    parser.add_argument("--cmd", help="Command to run")
    parser.add_argument("--timeout", type=int, help="Timeout in seconds")
    parser.add_argument("--notify", default="stderr", choices=["stderr", "slack", "discord", "telegram"])
    parser.add_argument("--always-notify", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    
    if args.command == "report" or (not args.cmd and not args.command):
        show_report(args.name, args.limit)
    elif args.cmd and args.name:
        exit_code = run_job(args.name, args.cmd, args.timeout, args.notify, args.always_notify)
        sys.exit(exit_code)
    else:
        parser.error("Use: --name NAME --cmd COMMAND, or: report")


if __name__ == "__main__":
    main()
