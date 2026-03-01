#!/usr/bin/env python3
"""
Time Tracker — Simple CLI time tracking for tasks and projects.

Track time spent on tasks with start/stop/report commands.
Data stored in JSON for easy integration with other tools.

Usage:
    python time_tracker.py start "Working on API refactor"
    python time_tracker.py stop
    python time_tracker.py status
    python time_tracker.py report --today
    python time_tracker.py report --week --project "backend"

No external dependencies required.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

DATA_FILE = Path.home() / ".local" / "share" / "time-tracker" / "entries.json"


def load_entries() -> list[dict]:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []


def save_entries(entries: list[dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(entries, indent=2))


def start_timer(description: str, project: str = "default"):
    entries = load_entries()
    # Check for running timer
    for e in entries:
        if not e.get("end"):
            print(f"⚠️  Timer already running: {e['description']}")
            print(f"   Started: {e['start']}")
            return
    
    entry = {
        "description": description,
        "project": project,
        "start": datetime.now().isoformat(),
        "end": None,
    }
    entries.append(entry)
    save_entries(entries)
    print(f"⏱️  Timer started: {description}")
    print(f"   Project: {project}")


def stop_timer():
    entries = load_entries()
    for e in reversed(entries):
        if not e.get("end"):
            e["end"] = datetime.now().isoformat()
            start = datetime.fromisoformat(e["start"])
            end = datetime.fromisoformat(e["end"])
            duration = end - start
            e["duration_minutes"] = round(duration.total_seconds() / 60, 1)
            save_entries(entries)
            print(f"⏹️  Timer stopped: {e['description']}")
            print(f"   Duration: {_format_duration(duration)}")
            return
    print("No active timer found.")


def show_status():
    entries = load_entries()
    for e in reversed(entries):
        if not e.get("end"):
            start = datetime.fromisoformat(e["start"])
            elapsed = datetime.now() - start
            print(f"⏱️  Running: {e['description']}")
            print(f"   Project: {e['project']}")
            print(f"   Elapsed: {_format_duration(elapsed)}")
            return
    print("No active timer.")


def generate_report(period: str = "today", project: str = None):
    entries = load_entries()
    now = datetime.now()
    
    if period == "today":
        start_filter = now.replace(hour=0, minute=0, second=0)
    elif period == "week":
        start_filter = now - timedelta(days=now.weekday())
        start_filter = start_filter.replace(hour=0, minute=0, second=0)
    elif period == "month":
        start_filter = now.replace(day=1, hour=0, minute=0, second=0)
    else:
        start_filter = datetime.min
    
    filtered = []
    for e in entries:
        if not e.get("end"):
            continue
        entry_start = datetime.fromisoformat(e["start"])
        if entry_start >= start_filter:
            if project and e.get("project", "").lower() != project.lower():
                continue
            filtered.append(e)
    
    if not filtered:
        print(f"No entries for {period}" + (f" (project: {project})" if project else ""))
        return
    
    total_minutes = sum(e.get("duration_minutes", 0) for e in filtered)
    by_project = {}
    for e in filtered:
        proj = e.get("project", "default")
        by_project.setdefault(proj, []).append(e)
    
    print(f"📊 Time Report — {period.title()}")
    if project:
        print(f"   Project filter: {project}")
    print(f"   Total: {_format_duration(timedelta(minutes=total_minutes))}")
    print(f"   Entries: {len(filtered)}\n")
    
    for proj, proj_entries in sorted(by_project.items()):
        proj_total = sum(e.get("duration_minutes", 0) for e in proj_entries)
        print(f"  📁 {proj} ({_format_duration(timedelta(minutes=proj_total))})")
        for e in proj_entries:
            dur = e.get("duration_minutes", 0)
            print(f"     • {e['description']} — {dur:.0f}m")
        print()


def _format_duration(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def main():
    parser = argparse.ArgumentParser(description="CLI time tracker")
    sub = parser.add_subparsers(dest="command")
    
    start_p = sub.add_parser("start", help="Start timer")
    start_p.add_argument("description", help="What you're working on")
    start_p.add_argument("--project", "-p", default="default", help="Project name")
    
    sub.add_parser("stop", help="Stop current timer")
    sub.add_parser("status", help="Show current timer")
    
    report_p = sub.add_parser("report", help="Generate report")
    report_p.add_argument("--today", action="store_const", const="today", dest="period")
    report_p.add_argument("--week", action="store_const", const="week", dest="period")
    report_p.add_argument("--month", action="store_const", const="month", dest="period")
    report_p.add_argument("--all", action="store_const", const="all", dest="period")
    report_p.add_argument("--project", help="Filter by project")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_timer(args.description, args.project)
    elif args.command == "stop":
        stop_timer()
    elif args.command == "status":
        show_status()
    elif args.command == "report":
        generate_report(args.period or "today", args.project)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
