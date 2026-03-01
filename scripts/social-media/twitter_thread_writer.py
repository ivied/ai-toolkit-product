#!/usr/bin/env python3
"""
Twitter/X Thread Writer — Generate and format tweet threads from long-form content.

Takes a blog post, article, or plain text and converts it into a properly formatted
Twitter thread with character limits, numbering, and hooks.

Usage:
    python twitter_thread_writer.py --input article.md
    python twitter_thread_writer.py --text "Your long text here"
    python twitter_thread_writer.py --input article.md --style punchy
    echo "Long text" | python twitter_thread_writer.py --stdin

Requirements:
    pip install openai  (optional, for AI-powered summarization)
"""

import argparse
import os
import re
import sys
import textwrap

CHAR_LIMIT = 280
THREAD_MARKER_LEN = 8  # " (X/Y) " format


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def create_thread(text: str, style: str = "default") -> list[str]:
    """Convert long text into a tweet thread."""
    # Clean up text
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Remove markdown links
    text = re.sub(r'[#*_`]', '', text)  # Remove markdown formatting
    
    sentences = split_into_sentences(text)
    
    if not sentences:
        return []
    
    # Build tweets by filling up to character limit
    tweets = []
    current = ""
    effective_limit = CHAR_LIMIT - THREAD_MARKER_LEN
    
    for sentence in sentences:
        if len(sentence) > effective_limit:
            # Split long sentence by clauses
            parts = re.split(r'[,;—–]', sentence)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if len(current) + len(part) + 2 <= effective_limit:
                    current = f"{current} {part}".strip() if current else part
                else:
                    if current:
                        tweets.append(current)
                    current = part
        elif len(current) + len(sentence) + 1 <= effective_limit:
            current = f"{current} {sentence}".strip() if current else sentence
        else:
            if current:
                tweets.append(current)
            current = sentence
    
    if current:
        tweets.append(current)
    
    # Add thread numbering
    total = len(tweets)
    numbered = []
    for i, tweet in enumerate(tweets, 1):
        marker = f" ({i}/{total})" if total > 1 else ""
        # Ensure we don't exceed limit with marker
        max_content = CHAR_LIMIT - len(marker)
        content = tweet[:max_content]
        numbered.append(f"{content}{marker}")
    
    # Style modifications
    if style == "punchy" and numbered:
        # Add hook to first tweet
        numbered[0] = "🧵 " + numbered[0]
        # Add CTA to last tweet
        if len(numbered) > 1:
            numbered[-1] = numbered[-1].replace(f"({total}/{total})", "").strip()
            numbered[-1] += "\n\n♻️ RT the first tweet if this was helpful!"
    
    return numbered


def create_thread_ai(text: str, api_key: str) -> list[str]:
    """Use AI to create a more engaging thread."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": "You are a Twitter thread expert. Convert the following text into an engaging tweet thread. Each tweet must be under 280 characters. Start with a hook. End with a CTA. Number each tweet as (X/Y). Output ONLY the tweets, separated by ---"
            }, {
                "role": "user",
                "content": text[:4000]
            }],
            max_tokens=2000,
        )
        
        content = resp.choices[0].message.content
        tweets = [t.strip() for t in content.split("---") if t.strip()]
        return tweets
    except Exception as e:
        print(f"AI generation failed: {e}. Falling back to rule-based.", file=sys.stderr)
        return create_thread(text, "punchy")


def main():
    parser = argparse.ArgumentParser(description="Convert text into Twitter threads")
    parser.add_argument("--input", help="Input file (markdown, txt)")
    parser.add_argument("--text", help="Direct text input")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--style", choices=["default", "punchy", "ai"], default="default")
    parser.add_argument("--preview", action="store_true", help="Show character counts")
    args = parser.parse_args()
    
    if args.input:
        with open(args.input) as f:
            text = f.read()
    elif args.text:
        text = args.text
    elif args.stdin or not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.error("Provide --input, --text, or pipe via stdin")
    
    if args.style == "ai":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            tweets = create_thread_ai(text, api_key)
        else:
            print("No OPENAI_API_KEY set, using rule-based mode", file=sys.stderr)
            tweets = create_thread(text, "punchy")
    else:
        tweets = create_thread(text, args.style)
    
    for i, tweet in enumerate(tweets):
        if args.preview:
            print(f"[{len(tweet)} chars]")
        print(tweet)
        if i < len(tweets) - 1:
            print("---")


if __name__ == "__main__":
    main()
