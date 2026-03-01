#!/usr/bin/env python3
"""
Price Monitor
=============
Monitor product prices on web pages and get notified when they drop.
Uses CSS selectors to extract prices. Stores history in JSON.

Usage:
    python price_monitor.py add "https://example.com/product" ".price" --name "Widget"
    python price_monitor.py check
    python price_monitor.py check --notify slack
    python price_monitor.py history "Widget"

Environment:
    SLACK_WEBHOOK_URL  — for Slack notifications
    TELEGRAM_BOT_TOKEN — for Telegram notifications  
    TELEGRAM_CHAT_ID   — Telegram chat ID for notifications
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import httpx
    from selectolax.parser import HTMLParser
except ImportError:
    print("Install dependencies: pip install httpx selectolax")
    sys.exit(1)

import os

DB_FILE = Path("price_monitor.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def load_db() -> dict:
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text())
    return {"products": {}, "history": {}}


def save_db(db: dict):
    DB_FILE.write_text(json.dumps(db, indent=2))


def extract_price(text: str) -> float | None:
    """Extract numeric price from text like '$19.99' or '€ 1.234,56'."""
    # Remove currency symbols and normalize
    cleaned = re.sub(r'[^\d.,]', '', text.strip())
    if not cleaned:
        return None
    # Handle European format (1.234,56 → 1234.56)
    if ',' in cleaned and '.' in cleaned:
        if cleaned.index(',') > cleaned.index('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Could be decimal comma or thousands
        parts = cleaned.split(',')
        if len(parts[-1]) <= 2:
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_price(url: str, selector: str) -> tuple[float | None, str]:
    """Fetch page and extract price using CSS selector."""
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        resp = client.get(url)
        resp.raise_for_status()

    tree = HTMLParser(resp.text)
    node = tree.css_first(selector)
    if not node:
        return None, f"Selector '{selector}' not found"

    raw = node.text(strip=True)
    price = extract_price(raw)
    return price, raw


def notify_slack(message: str):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return
    with httpx.Client() as client:
        client.post(url, json={"text": message})


def notify_telegram(message: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    with httpx.Client() as client:
        client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
        )


def cmd_add(args):
    db = load_db()
    name = args.name or args.url[:50]
    db["products"][name] = {
        "url": args.url,
        "selector": args.selector,
        "added": datetime.now().isoformat(),
        "threshold": args.threshold,
    }
    save_db(db)
    print(f"✅ Added '{name}'")

    # Do initial check
    price, raw = fetch_price(args.url, args.selector)
    if price:
        print(f"   Current price: {price} (raw: {raw})")
        db["history"].setdefault(name, []).append({
            "price": price, "raw": raw, "time": datetime.now().isoformat()
        })
        save_db(db)
    else:
        print(f"   ⚠ Could not extract price: {raw}")


def cmd_check(args):
    db = load_db()
    if not db["products"]:
        print("No products tracked. Use 'add' first.")
        return

    alerts = []
    for name, product in db["products"].items():
        price, raw = fetch_price(product["url"], product["selector"])
        history = db["history"].setdefault(name, [])

        if price is None:
            print(f"  ⚠ {name}: could not extract price ({raw})")
            continue

        prev = history[-1]["price"] if history else None
        change = ""
        if prev:
            diff = price - prev
            pct = (diff / prev) * 100
            if diff < 0:
                change = f" 📉 {pct:.1f}%"
            elif diff > 0:
                change = f" 📈 +{pct:.1f}%"

        history.append({"price": price, "raw": raw, "time": datetime.now().isoformat()})
        print(f"  {'✅' if price <= (product.get('threshold') or float('inf')) else '📊'} {name}: {price}{change}")

        # Check threshold
        threshold = product.get("threshold")
        if threshold and price <= threshold:
            alert = f"🔔 Price drop! {name}: {price} (threshold: {threshold})\n{product['url']}"
            alerts.append(alert)
            print(f"     🔔 Below threshold ({threshold})!")

    save_db(db)

    # Send notifications
    if alerts:
        combined = "\n\n".join(alerts)
        if args.notify in ("slack", "all"):
            notify_slack(combined)
        if args.notify in ("telegram", "all"):
            notify_telegram(combined)
        if args.notify:
            print(f"\n📬 Sent {len(alerts)} alert(s) via {args.notify}")


def cmd_history(args):
    db = load_db()
    name = args.name
    if name not in db["history"]:
        print(f"No history for '{name}'")
        return

    history = db["history"][name]
    print(f"\n📊 Price history: {name}")
    print(f"{'Date':<22} {'Price':>10}")
    print("─" * 33)
    for entry in history[-20:]:
        t = entry["time"][:16].replace("T", " ")
        print(f"  {t:<20} {entry['price']:>10.2f}")

    if len(history) >= 2:
        first, last = history[0]["price"], history[-1]["price"]
        change = ((last - first) / first) * 100
        print(f"\n  Overall: {first:.2f} → {last:.2f} ({change:+.1f}%)")


def cmd_list(args):
    db = load_db()
    if not db["products"]:
        print("No products tracked.")
        return
    for name, p in db["products"].items():
        history = db["history"].get(name, [])
        last = f"{history[-1]['price']:.2f}" if history else "?"
        print(f"  {name}: {last} — {p['url'][:60]}")


def main():
    parser = argparse.ArgumentParser(description="Monitor product prices")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add product to monitor")
    p_add.add_argument("url", help="Product URL")
    p_add.add_argument("selector", help="CSS selector for price element")
    p_add.add_argument("--name", help="Product name (default: URL)")
    p_add.add_argument("--threshold", type=float, help="Alert when price drops below this")
    p_add.set_defaults(func=cmd_add)

    p_check = sub.add_parser("check", help="Check all prices")
    p_check.add_argument("--notify", choices=["slack", "telegram", "all"], help="Send alerts")
    p_check.set_defaults(func=cmd_check)

    p_history = sub.add_parser("history", help="Show price history")
    p_history.add_argument("name", help="Product name")
    p_history.set_defaults(func=cmd_history)

    p_list = sub.add_parser("list", help="List tracked products")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
