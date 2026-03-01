#!/usr/bin/env python3
"""
Reddit Monitor — Track subreddits for keywords and new posts.

Monitor subreddits via RSS (no API key needed!) for keyword matches,
new posts, and trending discussions.

Usage:
    python reddit_monitor.py --subreddits python,machinelearning --keywords "project,tool,library"
    python reddit_monitor.py --subreddits startups --keywords "launch,feedback" --output json
    python reddit_monitor.py --subreddits programming --top --limit 10

Requirements:
    pip install feedparser requests
"""

import argparse
import json
import re
import sys
from datetime import datetime

try:
    import feedparser
    import requests
except ImportError:
    print("Install deps: pip install feedparser requests", file=sys.stderr)
    sys.exit(1)


def fetch_subreddit(subreddit, sort="new", limit=25):
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    resp = requests.get(url, headers={"User-Agent": "AI-Toolkit-Reddit-Monitor/1.0"}, timeout=15)
    
    if resp.status_code != 200:
        # Fallback to RSS
        feed = feedparser.parse(f"https://www.reddit.com/r/{subreddit}/{sort}/.rss")
        return [{
            "title": e.get("title", ""),
            "url": e.get("link", ""),
            "author": e.get("author", ""),
            "score": 0,
            "comments": 0,
            "created": e.get("published", ""),
            "selftext": e.get("summary", "")[:300],
            "subreddit": subreddit,
        } for e in feed.entries[:limit]]
    
    data = resp.json()
    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        posts.append({
            "title": d.get("title", ""),
            "url": f"https://reddit.com{d.get('permalink', '')}",
            "author": d.get("author", ""),
            "score": d.get("score", 0),
            "comments": d.get("num_comments", 0),
            "created": datetime.utcfromtimestamp(d.get("created_utc", 0)).isoformat(),
            "selftext": d.get("selftext", "")[:300],
            "subreddit": subreddit,
            "flair": d.get("link_flair_text", ""),
        })
    return posts


def filter_by_keywords(posts, keywords):
    if not keywords:
        return posts
    
    filtered = []
    for post in posts:
        searchable = f"{post['title']} {post.get('selftext', '')} {post.get('flair', '')}".lower()
        matched = [kw for kw in keywords if kw.lower() in searchable]
        if matched:
            post["matched_keywords"] = matched
            filtered.append(post)
    return filtered


def format_output(posts, fmt="text"):
    if fmt == "json":
        return json.dumps(posts, indent=2, ensure_ascii=False)
    
    lines = [f"# Reddit Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    lines.append(f"Found **{len(posts)}** matching posts.\n")
    
    for i, p in enumerate(posts, 1):
        lines.append(f"### {i}. {p['title']}")
        lines.append(f"  ⬆️ {p['score']} | 💬 {p['comments']} | 👤 u/{p['author']} | r/{p['subreddit']}")
        if p.get("matched_keywords"):
            lines.append(f"  🔑 Keywords: {', '.join(p['matched_keywords'])}")
        lines.append(f"  🔗 {p['url']}")
        if p.get("selftext"):
            lines.append(f"  > {p['selftext'][:150]}...")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Monitor Reddit subreddits")
    parser.add_argument("--subreddits", required=True, help="Comma-separated subreddits")
    parser.add_argument("--keywords", default="", help="Comma-separated keywords to filter")
    parser.add_argument("--sort", choices=["new", "hot", "top", "rising"], default="new")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--min-score", type=int, default=0)
    args = parser.parse_args()
    
    subreddits = [s.strip() for s in args.subreddits.split(",")]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    
    all_posts = []
    for sub in subreddits:
        print(f"Fetching r/{sub}...", file=sys.stderr)
        posts = fetch_subreddit(sub, args.sort, args.limit)
        all_posts.extend(posts)
    
    if keywords:
        all_posts = filter_by_keywords(all_posts, keywords)
    
    if args.min_score > 0:
        all_posts = [p for p in all_posts if p.get("score", 0) >= args.min_score]
    
    all_posts.sort(key=lambda p: p.get("score", 0), reverse=True)
    print(format_output(all_posts, args.output))


if __name__ == "__main__":
    main()
