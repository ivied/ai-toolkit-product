#!/usr/bin/env python3
"""
Pomodoro Timer — Focus timer with notifications and stats.

Usage:
    python pomodoro.py                    # Start 25min focus session
    python pomodoro.py --focus 45 --break 10
    python pomodoro.py --sessions 4       # 4 pomodoros then long break
    python pomodoro.py stats              # Show productivity stats

No external dependencies. Uses system notifications on macOS/Linux.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DATA = Path.home() / ".local" / "share" / "pomodoro" / "sessions.json"


def notify(title, message):
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], timeout=5)
        elif system == "Linux":
            subprocess.run(["notify-send", title, message], timeout=5)
    except Exception:
        pass
    # Terminal bell
    print("\a", end="", flush=True)


def countdown(minutes, label):
    total = int(minutes * 60)
    start = time.time()
    
    for remaining in range(total, 0, -1):
        mins, secs = divmod(remaining, 60)
        print(f"\r  {label}: {mins:02d}:{secs:02d} remaining  ", end="", flush=True)
        elapsed = time.time() - start
        expected = total - remaining + 1
        sleep_time = max(0, expected - elapsed)
        time.sleep(min(sleep_time, 1))
    
    print(f"\r  {label}: 00:00 — Done!          ")


def run_pomodoro(focus=25, short_break=5, long_break=15, sessions=4):
    print(f"🍅 Pomodoro — {focus}min focus / {short_break}min break / {sessions} sessions\n")
    
    completed = []
    for i in range(1, sessions + 1):
        print(f"Session {i}/{sessions}:")
        notify("🍅 Focus Time", f"Session {i}/{sessions} — {focus} minutes")
        
        start = datetime.now()
        countdown(focus, "🎯 Focus")
        end = datetime.now()
        
        completed.append({
            "session": i,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "focus_minutes": focus,
            "date": start.strftime("%Y-%m-%d"),
        })
        
        # Break
        if i < sessions:
            break_time = long_break if i % 4 == 0 else short_break
            notify("☕ Break Time", f"{break_time} minutes — stretch!")
            countdown(break_time, "☕ Break")
        print()
    
    notify("🎉 Done!", f"Completed {sessions} pomodoros!")
    print(f"🎉 Completed {sessions} pomodoros ({sessions * focus} minutes of focus)")
    
    # Save stats
    history = json.loads(DATA.read_text()) if DATA.exists() else []
    history.extend(completed)
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(history, indent=2))


def show_stats():
    if not DATA.exists():
        print("No pomodoro data yet."); return
    
    history = json.loads(DATA.read_text())
    
    total = len(history)
    total_minutes = sum(s.get("focus_minutes", 25) for s in history)
    
    from collections import Counter
    by_date = Counter(s.get("date", "unknown") for s in history)
    
    print(f"📊 Pomodoro Stats\n")
    print(f"  Total sessions: {total}")
    print(f"  Total focus time: {total_minutes // 60}h {total_minutes % 60}m")
    print(f"  Average per day: {total / max(len(by_date), 1):.1f} sessions\n")
    
    print("  Last 7 days:")
    for date, count in sorted(by_date.items())[-7:]:
        bar = "🍅" * count
        print(f"    {date}: {bar} ({count})")


def main():
    parser = argparse.ArgumentParser(description="Pomodoro focus timer")
    parser.add_argument("command", nargs="?", default="start", choices=["start", "stats"])
    parser.add_argument("--focus", type=int, default=25)
    parser.add_argument("--break", dest="short_break", type=int, default=5)
    parser.add_argument("--long-break", type=int, default=15)
    parser.add_argument("--sessions", type=int, default=4)
    args = parser.parse_args()
    
    if args.command == "stats":
        show_stats()
    else:
        try:
            run_pomodoro(args.focus, args.short_break, args.long_break, args.sessions)
        except KeyboardInterrupt:
            print("\n\n⏸️  Pomodoro paused.")

if __name__ == "__main__":
    main()
