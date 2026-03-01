#!/usr/bin/env python3
"""
LinkedIn Post Formatter — Format and optimize posts for LinkedIn.

Takes raw text and formats it for maximum LinkedIn engagement:
line breaks, hooks, CTAs, emoji placement, and character limits.

Usage:
    python linkedin_post_formatter.py --text "Your post content here"
    python linkedin_post_formatter.py --input draft.md --style storytelling
    python linkedin_post_formatter.py --text "..." --hook --cta --hashtags

No external dependencies required.
"""

import argparse
import re
import sys
import textwrap

CHAR_LIMIT = 3000
HOOKS = [
    "I {verb} something that changed everything.",
    "Stop {doing_thing}. Here's why →",
    "The biggest mistake I see in {industry}:",
    "Nobody talks about this, but...",
    "3 years ago, I {past_action}. Today, I {present_result}.",
    "Unpopular opinion about {topic}:",
    "{stat} of people get this wrong.",
]

CTAS = [
    "\n♻️ Repost if you agree\n👤 Follow me for more {topic} insights",
    "\n💬 What's your experience? Drop a comment below.",
    "\n🔔 Follow for daily tips on {topic}\n♻️ Share with someone who needs this",
    "\nAgree? Disagree? Let me know 👇",
]


def format_linkedin(text, add_hook=False, add_cta=False, hashtags=None,
                    style="default", topic="this"):
    """Format text for LinkedIn."""
    # Clean up
    text = text.strip()
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Remove MD links
    text = re.sub(r'#{1,6}\s+', '', text)  # Remove headers
    text = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', text)  # Remove bold/italic
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    # Apply style formatting
    if style == "storytelling":
        # Short lines for drama
        formatted = []
        for para in paragraphs:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for s in sentences:
                formatted.append(s)
                formatted.append("")  # Add blank line between sentences
        paragraphs = formatted
    
    elif style == "listicle":
        # Number the main points
        formatted = [paragraphs[0]] if paragraphs else []
        count = 1
        for para in paragraphs[1:]:
            if len(para) > 20 and not para.startswith(("•", "-", "1")):
                formatted.append(f"{count}. {para}")
                count += 1
            else:
                formatted.append(para)
        paragraphs = formatted
    
    elif style == "minimalist":
        # Very short, punchy lines
        formatted = []
        for para in paragraphs:
            words = para.split()
            current = []
            for word in words:
                current.append(word)
                if len(" ".join(current)) > 40:
                    formatted.append(" ".join(current))
                    formatted.append("")
                    current = []
            if current:
                formatted.append(" ".join(current))
                formatted.append("")
        paragraphs = formatted
    
    # Build final post
    parts = []
    
    if add_hook:
        import random
        hook = random.choice(HOOKS)
        hook = hook.replace("{topic}", topic).replace("{industry}", topic)
        hook = hook.replace("{verb}", "discovered").replace("{doing_thing}", "doing it wrong")
        hook = hook.replace("{past_action}", "started").replace("{present_result}", "see the results")
        hook = hook.replace("{stat}", "90%")
        parts.append(hook)
        parts.append("")
    
    parts.extend(paragraphs)
    
    if add_cta:
        import random
        cta = random.choice(CTAS).replace("{topic}", topic)
        parts.append(cta)
    
    if hashtags:
        tags = " ".join(f"#{h.strip('#')}" for h in hashtags)
        parts.append("")
        parts.append(tags)
    
    post = "\n".join(parts)
    
    # Enforce character limit
    if len(post) > CHAR_LIMIT:
        post = post[:CHAR_LIMIT - 3] + "..."
    
    return post


def main():
    parser = argparse.ArgumentParser(description="Format posts for LinkedIn")
    parser.add_argument("--text", help="Post text")
    parser.add_argument("--input", "-i", help="Input file")
    parser.add_argument("--style", choices=["default", "storytelling", "listicle", "minimalist"], default="default")
    parser.add_argument("--hook", action="store_true", help="Add an attention-grabbing hook")
    parser.add_argument("--cta", action="store_true", help="Add call-to-action")
    parser.add_argument("--hashtags", help="Comma-separated hashtags")
    parser.add_argument("--topic", default="this topic", help="Topic for hook/CTA personalization")
    parser.add_argument("--preview", action="store_true", help="Show character count and preview")
    args = parser.parse_args()
    
    if args.input:
        with open(args.input) as f: text = f.read()
    elif args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.error("Provide --text, --input, or pipe via stdin")
    
    hashtags = [h.strip() for h in args.hashtags.split(",")] if args.hashtags else None
    
    post = format_linkedin(text, args.hook, args.cta, hashtags, args.style, args.topic)
    
    if args.preview:
        visible = post[:150].split("\n\n")[0]
        print(f"📊 Characters: {len(post)}/{CHAR_LIMIT}")
        print(f"📱 Preview (above fold): \"{visible}...\"")
        print(f"{'='*50}\n")
    
    print(post)


if __name__ == "__main__":
    main()
