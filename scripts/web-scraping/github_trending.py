#!/usr/bin/env python3
"""
GitHub Trending Scraper — Fetch trending repositories by language/period.

Scrapes GitHub's trending page and outputs structured data. Great for
keeping up with popular projects or building weekly digests.

Usage:
    python github_trending.py                                  # All languages, daily
    python github_trending.py --language python --period weekly
    python github_trending.py --language rust --output json
    python github_trending.py --language javascript --min-stars 100

Requirements:
    pip install requests beautifulsoup4
"""

import argparse
import json
import re
import sys

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install deps: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)


def fetch_trending(language: str = "", period: str = "daily") -> list[dict]:
    """Fetch trending repos from GitHub."""
    url = f"https://github.com/trending/{language}"
    params = {"since": period}
    
    resp = requests.get(
        url,
        params=params,
        headers={"User-Agent": "GitHub-Trending-Scraper/1.0"},
        timeout=15,
    )
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    repos = []
    
    for article in soup.select("article.Box-row"):
        # Repo name
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        
        full_name = h2.get("href", "").strip("/")
        
        # Description
        p = article.select_one("p")
        description = p.get_text(strip=True) if p else ""
        
        # Language
        lang_span = article.select_one("[itemprop='programmingLanguage']")
        lang = lang_span.get_text(strip=True) if lang_span else ""
        
        # Stars
        stars_text = ""
        for link in article.select("a.Link--muted"):
            href = link.get("href", "")
            if "/stargazers" in href:
                stars_text = link.get_text(strip=True).replace(",", "")
                break
        
        # Stars today/this week
        period_stars = ""
        span = article.select_one("span.d-inline-block.float-sm-right")
        if span:
            period_stars = span.get_text(strip=True)
        
        repos.append({
            "name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": description,
            "language": lang,
            "stars": int(stars_text) if stars_text.isdigit() else 0,
            "period_stars": period_stars,
        })
    
    return repos


def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub trending repos")
    parser.add_argument("--language", default="", help="Programming language filter")
    parser.add_argument("--period", choices=["daily", "weekly", "monthly"], default="daily")
    parser.add_argument("--output", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--min-stars", type=int, default=0, help="Minimum total stars")
    parser.add_argument("--limit", type=int, default=25, help="Max results")
    args = parser.parse_args()
    
    repos = fetch_trending(args.language, args.period)
    
    if args.min_stars > 0:
        repos = [r for r in repos if r["stars"] >= args.min_stars]
    
    repos = repos[:args.limit]
    
    if args.output == "json":
        print(json.dumps(repos, indent=2, ensure_ascii=False))
    else:
        lang_label = args.language.capitalize() or "All Languages"
        print(f"# GitHub Trending — {lang_label} ({args.period})\n")
        for i, r in enumerate(repos, 1):
            print(f"**{i}. [{r['name']}]({r['url']})** ⭐ {r['stars']:,}")
            if r["language"]:
                print(f"   Language: {r['language']}")
            if r["description"]:
                print(f"   {r['description'][:120]}")
            if r["period_stars"]:
                print(f"   📈 {r['period_stars']}")
            print()


if __name__ == "__main__":
    main()
