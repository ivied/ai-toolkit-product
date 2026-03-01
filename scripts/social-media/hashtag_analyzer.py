#!/usr/bin/env python3
"""
Hashtag Analyzer — Analyze and suggest hashtags for social media posts.

Generates relevant hashtags based on content, checks popularity estimates,
and groups them by reach tier (high/medium/niche).

Usage:
    python hashtag_analyzer.py --text "Building AI agents with Python"
    python hashtag_analyzer.py --niche "machine learning" --count 30
    python hashtag_analyzer.py --input post.md --platform instagram

No API keys required for basic mode.
"""

import argparse
import json
import re
import sys
from collections import Counter

# Curated hashtag database by category
HASHTAG_DB = {
    "tech": {
        "high": ["#tech", "#coding", "#programming", "#developer", "#software", "#AI", "#python"],
        "medium": ["#webdev", "#devops", "#machinelearning", "#datascience", "#fullstack", "#javascript"],
        "niche": ["#buildinpublic", "#100DaysOfCode", "#techtwitter", "#codenewbie", "#learntocode"],
    },
    "ai": {
        "high": ["#AI", "#artificialintelligence", "#machinelearning", "#deeplearning", "#ChatGPT"],
        "medium": ["#NLP", "#computervision", "#LLM", "#generativeai", "#AItools"],
        "niche": ["#AIagents", "#promptengineering", "#RAG", "#finetuning", "#MLOps"],
    },
    "business": {
        "high": ["#entrepreneur", "#startup", "#business", "#marketing", "#growth"],
        "medium": ["#SaaS", "#indiehacker", "#solopreneur", "#ProductHunt", "#bootstrapped"],
        "niche": ["#buildinpublic", "#MRR", "#startuplife", "#microSaaS", "#ARR"],
    },
    "content": {
        "high": ["#contentcreator", "#socialmedia", "#marketing", "#digital", "#brand"],
        "medium": ["#contentmarketing", "#copywriting", "#SEO", "#blogging", "#newsletter"],
        "niche": ["#writingcommunity", "#contentcalendar", "#growthhacking", "#threadtips"],
    },
}

KEYWORD_TO_CATEGORY = {
    "python": "tech", "javascript": "tech", "react": "tech", "coding": "tech",
    "developer": "tech", "software": "tech", "web": "tech", "app": "tech",
    "api": "tech", "database": "tech", "cloud": "tech", "devops": "tech",
    "ai": "ai", "machine learning": "ai", "ml": "ai", "llm": "ai",
    "gpt": "ai", "neural": "ai", "deep learning": "ai", "agent": "ai",
    "prompt": "ai", "nlp": "ai", "data science": "ai",
    "startup": "business", "saas": "business", "business": "business",
    "entrepreneur": "business", "revenue": "business", "product": "business",
    "marketing": "content", "content": "content", "social": "content",
    "brand": "content", "seo": "content", "blog": "content",
}


def detect_categories(text: str) -> list[str]:
    """Detect relevant categories from text."""
    text_lower = text.lower()
    categories = Counter()
    
    for keyword, category in KEYWORD_TO_CATEGORY.items():
        if keyword in text_lower:
            categories[category] += 1
    
    if not categories:
        categories["tech"] = 1  # Default
    
    return [cat for cat, _ in categories.most_common(3)]


def extract_keywords(text: str) -> list[str]:
    """Extract potential hashtag keywords from text."""
    # Remove common words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "can", "shall",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "as", "into", "through", "during", "before", "after", "and",
                  "but", "or", "nor", "not", "so", "yet", "both", "either",
                  "this", "that", "these", "those", "i", "you", "he", "she",
                  "it", "we", "they", "my", "your", "his", "her", "its", "our"}
    
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words]
    
    # Get most common meaningful words
    counter = Counter(keywords)
    return [word for word, _ in counter.most_common(10)]


def generate_hashtags(text: str, count: int = 20, platform: str = "twitter") -> dict:
    """Generate hashtag suggestions."""
    categories = detect_categories(text)
    keywords = extract_keywords(text)
    
    # Collect hashtags from matching categories
    high = []
    medium = []
    niche = []
    
    for cat in categories:
        if cat in HASHTAG_DB:
            high.extend(HASHTAG_DB[cat]["high"])
            medium.extend(HASHTAG_DB[cat]["medium"])
            niche.extend(HASHTAG_DB[cat]["niche"])
    
    # Add keyword-based hashtags
    keyword_tags = [f"#{kw}" for kw in keywords[:5]]
    
    # Deduplicate
    high = list(dict.fromkeys(high))
    medium = list(dict.fromkeys(medium))
    niche = list(dict.fromkeys(niche))
    
    # Platform-specific limits
    limits = {"instagram": 30, "twitter": 5, "linkedin": 5, "tiktok": 10}
    max_tags = min(count, limits.get(platform, count))
    
    # Mix tiers: 30% high, 40% medium, 30% niche
    n_high = max(1, int(max_tags * 0.3))
    n_medium = max(1, int(max_tags * 0.4))
    n_niche = max_tags - n_high - n_medium
    
    selected = high[:n_high] + medium[:n_medium] + niche[:n_niche]
    
    return {
        "categories": categories,
        "keywords": keywords,
        "recommended": selected[:max_tags],
        "by_tier": {
            "high_reach": high[:10],
            "medium_reach": medium[:10],
            "niche": niche[:10],
        },
        "keyword_based": keyword_tags,
        "platform": platform,
        "total": len(selected),
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze and suggest hashtags")
    parser.add_argument("--text", help="Text to analyze")
    parser.add_argument("--input", help="Input file")
    parser.add_argument("--niche", help="Niche/topic for hashtag generation")
    parser.add_argument("--platform", default="twitter", choices=["twitter", "instagram", "linkedin", "tiktok"])
    parser.add_argument("--count", type=int, default=20, help="Number of hashtags")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    args = parser.parse_args()
    
    if args.input:
        with open(args.input) as f:
            text = f.read()
    elif args.text:
        text = args.text
    elif args.niche:
        text = args.niche
    else:
        parser.error("Provide --text, --input, or --niche")
    
    result = generate_hashtags(text, args.count, args.platform)
    
    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"🏷️  Hashtag Analysis for {args.platform.title()}\n")
        print(f"Detected categories: {', '.join(result['categories'])}")
        print(f"Keywords: {', '.join(result['keywords'][:5])}\n")
        print(f"📋 Recommended ({result['total']} tags):")
        print(f"   {' '.join(result['recommended'])}\n")
        print("By reach tier:")
        print(f"  🔥 High:   {' '.join(result['by_tier']['high_reach'][:5])}")
        print(f"  📈 Medium: {' '.join(result['by_tier']['medium_reach'][:5])}")
        print(f"  🎯 Niche:  {' '.join(result['by_tier']['niche'][:5])}")


if __name__ == "__main__":
    main()
