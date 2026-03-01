#!/usr/bin/env python3
"""
News Aggregator — Fetch and summarize top stories from multiple RSS feeds.

Combines stories from configurable RSS feeds, deduplicates by title similarity,
and outputs a clean digest in Markdown or JSON format.

Usage:
    python news_aggregator.py                          # Default tech feeds
    python news_aggregator.py --feeds urls.txt         # Custom feed list
    python news_aggregator.py --output json             # JSON output
    python news_aggregator.py --limit 20 --hours 24    # Last 24h, top 20

Requirements:
    pip install feedparser python-dateutil
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher

try:
    import feedparser
except ImportError:
    print("Install feedparser: pip install feedparser", file=sys.stderr)
    sys.exit(1)

from dateutil import parser as dateparser

DEFAULT_FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://www.reddit.com/r/programming/.rss",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://www.theverge.com/rss/index.xml",
]


def fetch_feed(url: str, hours: int = 48) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = []
    
    try:
        feed = feedparser.parse(url)
        source = feed.feed.get("title", url)
        
        for entry in feed.entries:
            published = None
            for date_field in ("published_parsed", "updated_parsed", "created_parsed"):
                if hasattr(entry, date_field) and getattr(entry, date_field):
                    try:
                        published = datetime(*getattr(entry, date_field)[:6], tzinfo=timezone.utc)
                    except (TypeError, ValueError):
                        pass
                    break
            
            if published and published < cutoff:
                continue
            
            articles.append({
                "title": entry.get("title", "Untitled"),
                "link": entry.get("link", ""),
                "source": source,
                "published": published.isoformat() if published else None,
                "summary": entry.get("summary", "")[:300],
            })
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
    
    return articles


def deduplicate(articles: list[dict], threshold: float = 0.7) -> list[dict]:
    """Remove near-duplicate articles by title similarity."""
    unique = []
    for article in articles:
        is_dup = False
        for existing in unique:
            ratio = SequenceMatcher(None, article["title"].lower(), existing["title"].lower()).ratio()
            if ratio > threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(article)
    return unique


def format_markdown(articles: list[dict]) -> str:
    """Format articles as Markdown digest."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# News Digest — {now}\n"]
    
    for i, a in enumerate(articles, 1):
        lines.append(f"## {i}. {a['title']}")
        lines.append(f"**Source:** {a['source']}  ")
        if a["published"]:
            lines.append(f"**Published:** {a['published'][:16]}  ")
        lines.append(f"**Link:** {a['link']}  ")
        if a["summary"]:
            clean = a["summary"].replace("<", "&lt;").replace(">", "&gt;")[:200]
            lines.append(f"\n> {clean}...")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Aggregate news from RSS feeds")
    parser.add_argument("--feeds", help="File with feed URLs (one per line)")
    parser.add_argument("--output", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--limit", type=int, default=30, help="Max articles (default: 30)")
    parser.add_argument("--hours", type=int, default=48, help="Look back N hours (default: 48)")
    args = parser.parse_args()
    
    if args.feeds:
        with open(args.feeds) as f:
            feeds = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        feeds = DEFAULT_FEEDS
    
    all_articles = []
    for url in feeds:
        all_articles.extend(fetch_feed(url, args.hours))
    
    # Sort by date (newest first), deduplicate
    all_articles.sort(key=lambda a: a["published"] or "", reverse=True)
    articles = deduplicate(all_articles)[:args.limit]
    
    if args.output == "json":
        print(json.dumps(articles, indent=2, ensure_ascii=False))
    else:
        print(format_markdown(articles))


if __name__ == "__main__":
    main()
