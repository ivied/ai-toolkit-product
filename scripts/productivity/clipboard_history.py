#!/usr/bin/env python3
"""
Clipboard History — Track and search clipboard history from CLI.

Maintains a searchable history of clipboard contents. Works on macOS (pbpaste)
and Linux (xclip/xsel).

Usage:
    python clipboard_history.py watch             # Start monitoring clipboard
    python clipboard_history.py list              # Show recent entries
    python clipboard_history.py search "keyword"  # Search history
    python clipboard_history.py get 3             # Get entry #3

No external dependencies (macOS/Linux clipboard tools required).
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DATA = Path.home() / ".local" / "share" / "clipboard-history" / "history.json"
MAX_ENTRIES = 500


def get_clipboard():
    system = platform.system()
    try:
        if system == "Darwin":
            return subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2).stdout
        elif system == "Linux":
            for cmd in [["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]]:
                try:
                    return subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout
                except FileNotFoundError:
                    continue
        return ""
    except Exception:
        return ""


def load(): return json.loads(DATA.read_text()) if DATA.exists() else []
def save(entries):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(entries[-MAX_ENTRIES:], indent=2))


def watch(interval=1.0):
    print(f"👀 Watching clipboard (Ctrl+C to stop)...")
    entries = load()
    last_hash = ""
    
    try:
        while True:
            content = get_clipboard()
            if content:
                h = hashlib.md5(content.encode()).hexdigest()
                if h != last_hash:
                    last_hash = h
                    entry = {
                        "content": content[:5000],
                        "timestamp": datetime.now().isoformat(),
                        "length": len(content),
                        "preview": content[:80].replace("\n", " "),
                    }
                    entries.append(entry)
                    save(entries)
                    print(f"  📋 [{len(entries)}] {entry['preview'][:60]}...")
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n✅ Saved {len(entries)} entries.")


def list_entries(limit=20):
    entries = load()
    if not entries:
        print("No clipboard history."); return
    
    print(f"📋 Clipboard History ({len(entries)} total, showing last {limit}):\n")
    for i, e in enumerate(entries[-limit:], len(entries) - limit + 1):
        ts = e.get("timestamp", "")[:16]
        print(f"  #{i} [{ts}] {e.get('preview', '')[:70]}")


def search_entries(query):
    entries = load()
    results = [(i, e) for i, e in enumerate(entries, 1) if query.lower() in e.get("content", "").lower()]
    
    if not results:
        print("No matches found."); return
    
    print(f"🔍 Found {len(results)} matches:\n")
    for i, e in results[-20:]:
        print(f"  #{i} [{e.get('timestamp', '')[:16]}] {e.get('preview', '')[:70]}")


def get_entry(index):
    entries = load()
    if 1 <= index <= len(entries):
        print(entries[index - 1]["content"])
    else:
        print(f"Invalid index. Range: 1-{len(entries)}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Clipboard history manager")
    sub = parser.add_subparsers(dest="cmd")
    
    sub.add_parser("watch")
    l = sub.add_parser("list"); l.add_argument("--limit", type=int, default=20)
    s = sub.add_parser("search"); s.add_argument("query")
    g = sub.add_parser("get"); g.add_argument("index", type=int)
    sub.add_parser("clear")
    
    args = parser.parse_args()
    if args.cmd == "watch": watch()
    elif args.cmd == "list": list_entries(args.limit)
    elif args.cmd == "search": search_entries(args.query)
    elif args.cmd == "get": get_entry(args.index)
    elif args.cmd == "clear": save([]); print("✅ History cleared.")
    else: parser.print_help()

if __name__ == "__main__":
    main()
