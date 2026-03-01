#!/usr/bin/env python3
"""
Site Change Detector — Monitor web pages for content changes.

Periodically checks URLs and detects when content changes. Useful for monitoring
product pages, documentation updates, competitor changes, or availability.

Usage:
    python site_change_detector.py --url "https://example.com/pricing"
    python site_change_detector.py --urls watchlist.txt --interval 3600
    python site_change_detector.py --url "https://example.com" --selector "div.price"

Requirements:
    pip install requests beautifulsoup4
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install deps: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)


STATE_FILE = Path.home() / ".cache" / "site-change-detector" / "state.json"


def load_state() -> dict:
    """Load previous content hashes."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    """Save content hashes."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_content(url: str, selector: str | None = None) -> str:
    """Fetch page content, optionally filtering by CSS selector."""
    resp = requests.get(
        url,
        headers={"User-Agent": "SiteChangeDetector/1.0"},
        timeout=30,
    )
    resp.raise_for_status()
    
    if selector:
        soup = BeautifulSoup(resp.text, "html.parser")
        elements = soup.select(selector)
        return "\n".join(el.get_text(strip=True) for el in elements)
    else:
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)


def content_hash(text: str) -> str:
    """Hash content for comparison."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def check_url(url: str, selector: str | None, state: dict) -> dict | None:
    """Check a single URL for changes. Returns change info or None."""
    try:
        content = fetch_content(url, selector)
        new_hash = content_hash(content)
        key = f"{url}|{selector or ''}"
        
        old_hash = state.get(key, {}).get("hash")
        old_content = state.get(key, {}).get("content", "")
        
        state[key] = {
            "hash": new_hash,
            "content": content[:5000],  # Store for diff
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "url": url,
        }
        
        if old_hash is None:
            return {"url": url, "status": "new", "message": "First check — baseline stored"}
        elif old_hash != new_hash:
            return {
                "url": url,
                "status": "changed",
                "message": f"Content changed (hash {old_hash} → {new_hash})",
                "old_preview": old_content[:200],
                "new_preview": content[:200],
            }
        return None  # No change
        
    except Exception as e:
        return {"url": url, "status": "error", "message": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Monitor web pages for changes")
    parser.add_argument("--url", help="Single URL to check")
    parser.add_argument("--urls", help="File with URLs (one per line, optional CSS selector after |)")
    parser.add_argument("--selector", help="CSS selector to monitor specific element")
    parser.add_argument("--interval", type=int, default=0, help="Re-check interval in seconds (0=once)")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    args = parser.parse_args()
    
    if not args.url and not args.urls:
        parser.error("Provide --url or --urls")
    
    # Build URL list
    targets = []
    if args.url:
        targets.append((args.url, args.selector))
    if args.urls:
        with open(args.urls) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|", 1)
                url = parts[0].strip()
                sel = parts[1].strip() if len(parts) > 1 else None
                targets.append((url, sel))
    
    state = load_state()
    
    while True:
        changes = []
        for url, selector in targets:
            result = check_url(url, selector, state)
            if result:
                changes.append(result)
        
        save_state(state)
        
        if changes:
            if args.output == "json":
                print(json.dumps(changes, indent=2))
            else:
                for c in changes:
                    icon = {"new": "🆕", "changed": "🔄", "error": "❌"}.get(c["status"], "?")
                    print(f"{icon} [{c['status'].upper()}] {c['url']}")
                    print(f"   {c['message']}")
                    if "new_preview" in c:
                        print(f"   Preview: {c['new_preview'][:100]}...")
                    print()
        else:
            if args.output == "text":
                print(f"✅ No changes detected ({len(targets)} URLs checked)")
        
        if args.interval <= 0:
            break
        
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
