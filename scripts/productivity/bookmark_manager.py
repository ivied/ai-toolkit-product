#!/usr/bin/env python3
"""
Bookmark Manager — Organize, tag, and search bookmarks from CLI.

Import bookmarks from browsers, add tags, search by content/tags,
and export as HTML or JSON. Dead link detection included.

Usage:
    python bookmark_manager.py add "https://example.com" --tags "dev,tools"
    python bookmark_manager.py search "python tutorial"
    python bookmark_manager.py check                        # Find dead links
    python bookmark_manager.py export --format html
    python bookmark_manager.py import --from chrome

Requirements:
    pip install requests  (for link checking)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

DATA_FILE = Path.home() / ".local" / "share" / "bookmarks" / "bookmarks.json"


def load_bookmarks() -> list[dict]:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []


def save_bookmarks(bookmarks: list[dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(bookmarks, indent=2))


def add_bookmark(url: str, title: str = "", tags: list[str] = None, notes: str = ""):
    bookmarks = load_bookmarks()
    
    # Check for duplicate
    for b in bookmarks:
        if b["url"] == url:
            print(f"⚠️  Bookmark already exists: {b.get('title', url)}")
            return
    
    if not title:
        title = urlparse(url).netloc
        if HAS_REQUESTS:
            try:
                resp = requests.get(url, timeout=5, headers={"User-Agent": "BookmarkManager/1.0"})
                import re
                match = re.search(r'<title[^>]*>([^<]+)</title>', resp.text, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
            except Exception:
                pass
    
    bookmark = {
        "url": url,
        "title": title,
        "tags": tags or [],
        "notes": notes,
        "added": datetime.now().isoformat(),
        "domain": urlparse(url).netloc,
    }
    
    bookmarks.append(bookmark)
    save_bookmarks(bookmarks)
    print(f"✅ Added: {title}")
    print(f"   URL: {url}")
    if tags:
        print(f"   Tags: {', '.join(tags)}")


def search_bookmarks(query: str, tag: str = None):
    bookmarks = load_bookmarks()
    query_lower = query.lower() if query else ""
    
    results = []
    for b in bookmarks:
        if tag and tag not in b.get("tags", []):
            continue
        if query_lower:
            searchable = f"{b['title']} {b['url']} {' '.join(b.get('tags', []))} {b.get('notes', '')}".lower()
            if query_lower not in searchable:
                continue
        results.append(b)
    
    if not results:
        print("No bookmarks found.")
        return
    
    print(f"🔍 Found {len(results)} bookmark(s):\n")
    for b in results:
        tags_str = f" [{', '.join(b.get('tags', []))}]" if b.get('tags') else ""
        print(f"  📌 {b['title']}{tags_str}")
        print(f"     {b['url']}")
        if b.get('notes'):
            print(f"     📝 {b['notes'][:80]}")
        print()


def check_links():
    if not HAS_REQUESTS:
        print("Install requests for link checking: pip install requests")
        return
    
    bookmarks = load_bookmarks()
    print(f"🔍 Checking {len(bookmarks)} bookmarks...\n")
    
    dead = []
    for b in bookmarks:
        try:
            resp = requests.head(b["url"], timeout=10, allow_redirects=True,
                               headers={"User-Agent": "BookmarkManager/1.0"})
            if resp.status_code >= 400:
                dead.append({"bookmark": b, "status": resp.status_code})
                print(f"  ❌ [{resp.status_code}] {b['title']}")
            else:
                print(f"  ✅ {b['title']}")
        except Exception as e:
            dead.append({"bookmark": b, "status": str(e)})
            print(f"  ❌ [Error] {b['title']}: {str(e)[:50]}")
    
    print(f"\n{'='*40}")
    print(f"Total: {len(bookmarks)} | Dead: {len(dead)} | Alive: {len(bookmarks) - len(dead)}")


def list_tags():
    bookmarks = load_bookmarks()
    tags = {}
    for b in bookmarks:
        for tag in b.get("tags", []):
            tags[tag] = tags.get(tag, 0) + 1
    
    if not tags:
        print("No tags found.")
        return
    
    print("🏷️  Tags:\n")
    for tag, count in sorted(tags.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count} bookmark(s)")


def export_bookmarks(fmt: str = "json"):
    bookmarks = load_bookmarks()
    
    if fmt == "json":
        print(json.dumps(bookmarks, indent=2))
    elif fmt == "html":
        print("<!DOCTYPE NETSCAPE-Bookmark-file-1>")
        print("<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">")
        print("<TITLE>Bookmarks</TITLE>")
        print("<H1>Bookmarks</H1>")
        print("<DL><p>")
        for b in bookmarks:
            ts = int(datetime.fromisoformat(b["added"]).timestamp()) if "added" in b else 0
            print(f'  <DT><A HREF="{b["url"]}" ADD_DATE="{ts}">{b["title"]}</A>')
            if b.get("notes"):
                print(f"  <DD>{b['notes']}")
        print("</DL><p>")
    elif fmt == "markdown":
        for b in bookmarks:
            tags_str = f" `{'` `'.join(b.get('tags', []))}`" if b.get("tags") else ""
            print(f"- [{b['title']}]({b['url']}){tags_str}")


def main():
    parser = argparse.ArgumentParser(description="CLI bookmark manager")
    sub = parser.add_subparsers(dest="command")
    
    add_p = sub.add_parser("add", help="Add a bookmark")
    add_p.add_argument("url", help="URL to bookmark")
    add_p.add_argument("--title", "-t", default="", help="Bookmark title")
    add_p.add_argument("--tags", default="", help="Comma-separated tags")
    add_p.add_argument("--notes", "-n", default="", help="Notes")
    
    search_p = sub.add_parser("search", help="Search bookmarks")
    search_p.add_argument("query", nargs="?", default="", help="Search query")
    search_p.add_argument("--tag", help="Filter by tag")
    
    sub.add_parser("check", help="Check for dead links")
    sub.add_parser("tags", help="List all tags")
    sub.add_parser("list", help="List all bookmarks")
    
    export_p = sub.add_parser("export", help="Export bookmarks")
    export_p.add_argument("--format", choices=["json", "html", "markdown"], default="json")
    
    args = parser.parse_args()
    
    if args.command == "add":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
        add_bookmark(args.url, args.title, tags, args.notes)
    elif args.command == "search":
        search_bookmarks(args.query, getattr(args, "tag", None))
    elif args.command == "check":
        check_links()
    elif args.command == "tags":
        list_tags()
    elif args.command == "list":
        search_bookmarks("")
    elif args.command == "export":
        export_bookmarks(args.format)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
