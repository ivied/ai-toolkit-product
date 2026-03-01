#!/usr/bin/env python3
"""
Job Scraper — Monitor job boards for matching positions via RSS/API.

Scrapes job listings from multiple sources (RemoteOK, GitHub Jobs format,
HN Who's Hiring) and filters by keywords. Outputs matches as Markdown or JSON.

Usage:
    python job_scraper.py --keywords "python,backend,remote"
    python job_scraper.py --keywords "react,frontend" --output json
    python job_scraper.py --keywords "data,ml" --exclude "senior,lead"

Requirements:
    pip install feedparser requests
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

try:
    import requests
    import feedparser
except ImportError:
    print("Install deps: pip install feedparser requests", file=sys.stderr)
    sys.exit(1)


def fetch_remoteok(keywords: list[str]) -> list[dict]:
    """Fetch jobs from RemoteOK API."""
    jobs = []
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "AI-Toolkit-Job-Scraper/1.0"},
            timeout=15,
        )
        data = resp.json()
        
        for item in data[1:]:  # First item is metadata
            title = item.get("position", "")
            company = item.get("company", "")
            description = item.get("description", "")
            tags = " ".join(item.get("tags", []))
            searchable = f"{title} {company} {description} {tags}".lower()
            
            if any(kw.lower() in searchable for kw in keywords):
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": item.get("location", "Remote"),
                    "url": item.get("url", ""),
                    "date": item.get("date", ""),
                    "tags": item.get("tags", []),
                    "salary": item.get("salary_min", ""),
                    "source": "RemoteOK",
                })
    except Exception as e:
        print(f"Warning: RemoteOK fetch failed: {e}", file=sys.stderr)
    
    return jobs


def fetch_hn_hiring(keywords: list[str]) -> list[dict]:
    """Fetch from HN Who's Hiring (latest monthly thread)."""
    jobs = []
    try:
        # Search for latest "Who is hiring" thread
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": "Ask HN: Who is hiring",
                "tags": "ask_hn",
                "numericFilters": "created_at_i>0",
            },
            timeout=15,
        )
        hits = resp.json().get("hits", [])
        
        if not hits:
            return jobs
        
        # Get comments from latest thread
        thread_id = hits[0]["objectID"]
        resp = requests.get(
            f"https://hn.algolia.com/api/v1/items/{thread_id}",
            timeout=15,
        )
        children = resp.json().get("children", [])
        
        for comment in children[:200]:  # Limit to first 200 comments
            text = comment.get("text", "")
            if not text:
                continue
            
            searchable = text.lower()
            if any(kw.lower() in searchable for kw in keywords):
                # Extract company name (usually first line)
                first_line = re.sub(r"<[^>]+>", "", text).split("\n")[0][:100]
                jobs.append({
                    "title": first_line,
                    "company": "",
                    "location": "",
                    "url": f"https://news.ycombinator.com/item?id={comment.get('id', '')}",
                    "date": comment.get("created_at", ""),
                    "tags": keywords,
                    "salary": "",
                    "source": "HN Who's Hiring",
                })
    except Exception as e:
        print(f"Warning: HN fetch failed: {e}", file=sys.stderr)
    
    return jobs


def filter_exclude(jobs: list[dict], exclude: list[str]) -> list[dict]:
    """Remove jobs matching exclude keywords."""
    if not exclude:
        return jobs
    
    filtered = []
    for job in jobs:
        searchable = f"{job['title']} {job['company']}".lower()
        if not any(ex.lower() in searchable for ex in exclude):
            filtered.append(job)
    return filtered


def format_output(jobs: list[dict], fmt: str) -> str:
    """Format job listings."""
    if fmt == "json":
        return json.dumps(jobs, indent=2, ensure_ascii=False)
    
    lines = [f"# Job Matches — {datetime.now().strftime('%Y-%m-%d')}\n"]
    lines.append(f"Found **{len(jobs)}** matching positions.\n")
    
    for i, j in enumerate(jobs, 1):
        lines.append(f"### {i}. {j['title']}")
        if j["company"]:
            lines.append(f"**Company:** {j['company']}  ")
        if j["location"]:
            lines.append(f"**Location:** {j['location']}  ")
        if j["salary"]:
            lines.append(f"**Salary:** {j['salary']}  ")
        lines.append(f"**Source:** {j['source']}  ")
        lines.append(f"**Link:** {j['url']}")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scrape job boards for matching positions")
    parser.add_argument("--keywords", required=True, help="Comma-separated keywords")
    parser.add_argument("--exclude", default="", help="Comma-separated exclusion keywords")
    parser.add_argument("--output", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()
    
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    exclude = [e.strip() for e in args.exclude.split(",") if e.strip()]
    
    print(f"Searching for: {', '.join(keywords)}", file=sys.stderr)
    
    all_jobs = []
    all_jobs.extend(fetch_remoteok(keywords))
    all_jobs.extend(fetch_hn_hiring(keywords))
    
    jobs = filter_exclude(all_jobs, exclude)
    print(format_output(jobs, args.output))


if __name__ == "__main__":
    main()
