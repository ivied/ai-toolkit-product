#!/usr/bin/env python3
"""
Product Tracker - Track product launches and updates across platforms
Monitors Product Hunt, Hacker News, Reddit, and more
"""

import os
import json
import requests
from datetime import datetime
from typing import List, Dict

class ProductTracker:
    def __init__(self, keywords: List[str] = None):
        self.keywords = keywords or ['saas', 'ai', 'tool']
        self.products = []

    def fetch_producthunt(self) -> List[Dict]:
        """Fetch products from Product Hunt"""
        products = []
        try:
            # Product Hunt public API (limited)
            url = "https://api.producthunt.com/v2/api/graphql"
            # Note: Requires API token for full access
            # Using public RSS feed as alternative
            rss_url = "https://www.producthunt.com/feed"
            import feedparser
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:20]:
                title = entry.get('title', '')
                if any(kw.lower() in title.lower() for kw in self.keywords):
                    products.append({
                        'name': title,
                        'url': entry.get('link', ''),
                        'description': entry.get('summary', '')[:200],
                        'published': entry.get('published', ''),
                        'source': 'Product Hunt',
                        'tags': [tag['term'] for tag in entry.get('tags', [])]
                    })
        except Exception as e:
            print(f"Error fetching from Product Hunt: {e}")

        return products

    def fetch_hackernews_show(self) -> List[Dict]:
        """Fetch 'Show HN' posts from Hacker News"""
        products = []
        try:
            url = "https://hn.algolia.com/api/v1/search_by_date?query=Show%20HN&tags=story&hitsPerPage=50"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for hit in data['hits']:
                    title = hit.get('title', '')
                    text = hit.get('story_text', '')
                    combined = f"{title} {text}".lower()

                    if any(kw.lower() in combined for kw in self.keywords):
                        products.append({
                            'name': title.replace('Show HN:', '').strip(),
                            'url': hit.get('url') or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                            'description': text[:200],
                            'published': hit.get('created_at', ''),
                            'source': 'Hacker News',
                            'points': hit.get('points', 0),
                            'comments': hit.get('num_comments', 0)
                        })
        except Exception as e:
            print(f"Error fetching from Hacker News: {e}")

        return products

    def fetch_reddit_launches(self, subreddits: List[str] = None) -> List[Dict]:
        """Fetch product launches from relevant subreddits"""
        products = []
        subreddits = subreddits or ['SideProject', 'roastmystartup', 'indiehackers', 'EntrepreneurRideAlong']

        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=25"
                headers = {'User-Agent': 'ProductTracker/1.0'}
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    for post in data['data']['children']:
                        post_data = post['data']
                        title = post_data.get('title', '')
                        selftext = post_data.get('selftext', '')
                        combined = f"{title} {selftext}".lower()

                        if any(kw.lower() in combined for kw in self.keywords):
                            products.append({
                                'name': title,
                                'url': post_data.get('url', ''),
                                'description': selftext[:200],
                                'published': datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                                'source': f"r/{subreddit}",
                                'upvotes': post_data.get('score', 0),
                                'comments': post_data.get('num_comments', 0)
                            })
            except Exception as e:
                print(f"Error fetching from r/{subreddit}: {e}")

        return products

    def fetch_betalist(self) -> List[Dict]:
        """Fetch from BetaList (startups in beta)"""
        products = []
        try:
            url = "https://betalist.com/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')

                # Parse BetaList entries
                entries = soup.find_all('div', class_='startup')[:20]
                for entry in entries:
                    try:
                        name_elem = entry.find('h2')
                        desc_elem = entry.find('p', class_='pitch')

                        if name_elem and desc_elem:
                            name = name_elem.get_text(strip=True)
                            description = desc_elem.get_text(strip=True)
                            link_elem = entry.find('a', href=True)

                            combined = f"{name} {description}".lower()
                            if any(kw.lower() in combined for kw in self.keywords):
                                products.append({
                                    'name': name,
                                    'url': link_elem['href'] if link_elem else '',
                                    'description': description,
                                    'published': datetime.now().isoformat(),
                                    'source': 'BetaList'
                                })
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"Error fetching from BetaList: {e}")

        return products

    def track_all(self) -> List[Dict]:
        """Track products from all sources"""
        print("Tracking Product Hunt...")
        self.products.extend(self.fetch_producthunt())

        print("Tracking Hacker News Show HN...")
        self.products.extend(self.fetch_hackernews_show())

        print("Tracking Reddit...")
        self.products.extend(self.fetch_reddit_launches())

        print("Tracking BetaList...")
        self.products.extend(self.fetch_betalist())

        # Remove duplicates based on name
        seen_names = set()
        unique_products = []
        for product in self.products:
            name_lower = product['name'].lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_products.append(product)

        self.products = unique_products
        return self.products

    def save_results(self, filename: str = "products.json"):
        """Save tracked products to JSON file"""
        output = {
            'tracked_at': datetime.now().isoformat(),
            'keywords': self.keywords,
            'total_products': len(self.products),
            'products': self.products
        }
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Saved {len(self.products)} products to {filename}")

    def export_markdown(self, filename: str = "products.md"):
        """Export as Markdown file"""
        md = f"# Product Tracker Report\n\n"
        md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        md += f"**Keywords:** {', '.join(self.keywords)}\n"
        md += f"**Total Products:** {len(self.products)}\n\n"
        md += "---\n\n"

        for product in self.products:
            md += f"## {product['name']}\n\n"
            md += f"**Source:** {product['source']}\n"
            md += f"**URL:** {product['url']}\n"
            md += f"**Published:** {product['published']}\n\n"
            md += f"{product['description']}\n\n"

            if 'points' in product:
                md += f"**Points:** {product['points']} | **Comments:** {product.get('comments', 0)}\n\n"
            elif 'upvotes' in product:
                md += f"**Upvotes:** {product['upvotes']} | **Comments:** {product.get('comments', 0)}\n\n"

            md += "---\n\n"

        with open(filename, 'w') as f:
            f.write(md)
        print(f"Exported Markdown to {filename}")

    def print_summary(self):
        """Print summary of tracked products"""
        print(f"\n{'='*60}")
        print(f"Tracked {len(self.products)} products matching keywords: {', '.join(self.keywords)}")
        print(f"{'='*60}\n")

        # Group by source
        by_source = {}
        for product in self.products:
            source = product['source']
            by_source[source] = by_source.get(source, 0) + 1

        for source, count in by_source.items():
            print(f"{source}: {count} products")


def main():
    keywords = os.getenv('PRODUCT_KEYWORDS', 'saas,ai,tool').split(',')
    output_json = os.getenv('OUTPUT_JSON', 'products.json')
    output_md = os.getenv('OUTPUT_MD', 'products.md')

    tracker = ProductTracker(keywords)
    tracker.track_all()
    tracker.print_summary()
    tracker.save_results(output_json)
    tracker.export_markdown(output_md)


if __name__ == '__main__':
    main()
