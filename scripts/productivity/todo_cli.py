#!/usr/bin/env python3
"""
Todo CLI — Minimal task manager with priorities and projects.

Usage:
    python todo_cli.py add "Buy groceries" --priority high
    python todo_cli.py add "Code review" --project work --due 2024-03-15
    python todo_cli.py list
    python todo_cli.py list --project work --priority high
    python todo_cli.py done 3
    python todo_cli.py report

No external dependencies required.
"""

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path

DATA = Path.home() / ".local" / "share" / "todo-cli" / "todos.json"
PRIORITIES = {"low": 0, "medium": 1, "high": 2, "urgent": 3}
PRIORITY_ICONS = {"low": "⬜", "medium": "🟡", "high": "🟠", "urgent": "🔴"}


def load(): return json.loads(DATA.read_text()) if DATA.exists() else []
def save(todos):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(todos, indent=2))


def add_todo(text, priority="medium", project="inbox", due=None):
    todos = load()
    todo = {
        "id": max((t["id"] for t in todos), default=0) + 1,
        "text": text, "priority": priority, "project": project,
        "due": due, "done": False, "created": datetime.now().isoformat(),
    }
    todos.append(todo)
    save(todos)
    print(f"✅ #{todo['id']}: {text} [{priority}]" + (f" (due: {due})" if due else ""))


def list_todos(project=None, priority=None, show_done=False):
    todos = load()
    filtered = [t for t in todos if (show_done or not t["done"])
                and (not project or t["project"] == project)
                and (not priority or t["priority"] == priority)]
    
    filtered.sort(key=lambda t: (-PRIORITIES.get(t["priority"], 0), t.get("due") or "9999"))
    
    if not filtered:
        print("📋 No tasks found.")
        return
    
    current_project = None
    for t in filtered:
        if t["project"] != current_project:
            current_project = t["project"]
            print(f"\n📁 {current_project}")
        
        icon = PRIORITY_ICONS.get(t["priority"], "⬜")
        check = "✓" if t["done"] else " "
        due = f" (due: {t['due']})" if t.get("due") else ""
        overdue = ""
        if t.get("due") and not t["done"]:
            try:
                if date.fromisoformat(t["due"]) < date.today():
                    overdue = " ⚠️ OVERDUE"
            except ValueError:
                pass
        
        print(f"  [{check}] {icon} #{t['id']}: {t['text']}{due}{overdue}")


def mark_done(todo_id):
    todos = load()
    for t in todos:
        if t["id"] == todo_id:
            t["done"] = True
            t["completed"] = datetime.now().isoformat()
            save(todos)
            print(f"✅ Completed: #{todo_id} — {t['text']}")
            return
    print(f"❌ Todo #{todo_id} not found.")


def delete_todo(todo_id):
    todos = load()
    todos = [t for t in todos if t["id"] != todo_id]
    save(todos)
    print(f"🗑️  Deleted #{todo_id}")


def report():
    todos = load()
    total = len(todos)
    done = sum(1 for t in todos if t["done"])
    pending = total - done
    overdue = sum(1 for t in todos if not t["done"] and t.get("due")
                  and date.fromisoformat(t["due"]) < date.today())
    
    by_project = {}
    for t in todos:
        p = t["project"]
        by_project.setdefault(p, {"total": 0, "done": 0})
        by_project[p]["total"] += 1
        if t["done"]:
            by_project[p]["done"] += 1
    
    print(f"📊 Todo Report")
    print(f"   Total: {total} | Done: {done} | Pending: {pending} | Overdue: {overdue}\n")
    for p, stats in sorted(by_project.items()):
        pct = int(stats["done"] / stats["total"] * 100) if stats["total"] else 0
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  📁 {p}: {bar} {pct}% ({stats['done']}/{stats['total']})")


def main():
    parser = argparse.ArgumentParser(description="Minimal todo CLI")
    sub = parser.add_subparsers(dest="cmd")
    
    a = sub.add_parser("add")
    a.add_argument("text"); a.add_argument("--priority", "-p", default="medium", choices=PRIORITIES.keys())
    a.add_argument("--project", default="inbox"); a.add_argument("--due", "-d")
    
    l = sub.add_parser("list")
    l.add_argument("--project"); l.add_argument("--priority", choices=PRIORITIES.keys())
    l.add_argument("--all", action="store_true", dest="show_done")
    
    d = sub.add_parser("done"); d.add_argument("id", type=int)
    dl = sub.add_parser("delete"); dl.add_argument("id", type=int)
    sub.add_parser("report")
    
    args = parser.parse_args()
    cmds = {"add": lambda: add_todo(args.text, args.priority, args.project, args.due),
            "list": lambda: list_todos(args.project, args.priority, args.show_done),
            "done": lambda: mark_done(args.id), "delete": lambda: delete_todo(args.id),
            "report": report}
    
    if args.cmd in cmds: cmds[args.cmd]()
    else: parser.print_help()


if __name__ == "__main__":
    main()
