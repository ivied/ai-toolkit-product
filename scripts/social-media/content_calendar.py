#!/usr/bin/env python3
"""
Content Calendar Generator — Create a social media content calendar.

Generates a structured content calendar with post ideas, hashtags, and
scheduling suggestions based on your niche and posting frequency.

Usage:
    python content_calendar.py --niche "AI tools" --weeks 4
    python content_calendar.py --niche "fitness" --platforms twitter,linkedin
    python content_calendar.py --niche "SaaS" --output json

Requirements:
    pip install openai  (for AI-generated ideas; works without it using templates)
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta

POST_TYPES = [
    {"type": "Educational", "emoji": "📚", "template": "How to {action} with {tool}"},
    {"type": "Tip", "emoji": "💡", "template": "Quick tip: {insight}"},
    {"type": "Case Study", "emoji": "📊", "template": "How {who} achieved {result}"},
    {"type": "Behind the Scenes", "emoji": "🎬", "template": "What building {project} looks like"},
    {"type": "Thread", "emoji": "🧵", "template": "Everything I learned about {topic}"},
    {"type": "Poll", "emoji": "📊", "template": "What's your preferred {choice}?"},
    {"type": "Meme/Humor", "emoji": "😂", "template": "When {relatable_situation}"},
    {"type": "Tool Review", "emoji": "🔧", "template": "I tried {tool} for a week"},
    {"type": "Hot Take", "emoji": "🔥", "template": "Unpopular opinion: {opinion}"},
    {"type": "Resource Share", "emoji": "📎", "template": "{count} resources for {topic}"},
    {"type": "Story", "emoji": "📖", "template": "The story of {event}"},
    {"type": "Question", "emoji": "❓", "template": "What's your biggest challenge with {topic}?"},
]

BEST_TIMES = {
    "twitter": ["9:00 AM", "12:00 PM", "5:00 PM"],
    "linkedin": ["7:30 AM", "12:00 PM", "5:30 PM"],
    "instagram": ["11:00 AM", "1:00 PM", "7:00 PM"],
    "tiktok": ["7:00 AM", "10:00 AM", "7:00 PM"],
}


def generate_calendar_template(niche: str, weeks: int, platforms: list[str], posts_per_week: int) -> list[dict]:
    """Generate calendar using templates (no AI needed)."""
    calendar = []
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate posting days
    if posts_per_week <= 3:
        post_days = [0, 2, 4][:posts_per_week]  # Mon, Wed, Fri
    elif posts_per_week <= 5:
        post_days = [0, 1, 2, 3, 4][:posts_per_week]  # Weekdays
    else:
        post_days = list(range(7))[:posts_per_week]
    
    for week in range(weeks):
        for day_offset in post_days:
            post_date = start_date + timedelta(weeks=week, days=day_offset)
            post_type = random.choice(POST_TYPES)
            platform = random.choice(platforms)
            best_time = random.choice(BEST_TIMES.get(platform, ["12:00 PM"]))
            
            calendar.append({
                "date": post_date.strftime("%Y-%m-%d"),
                "day": post_date.strftime("%A"),
                "time": best_time,
                "platform": platform,
                "type": post_type["type"],
                "emoji": post_type["emoji"],
                "idea": post_type["template"].format(
                    action="get started",
                    tool=niche,
                    insight=f"about {niche}",
                    who="we",
                    result=f"success in {niche}",
                    project=f"{niche} project",
                    topic=niche,
                    choice=f"{niche} approach",
                    relatable_situation=f"you're deep in {niche}",
                    opinion=f"{niche} doesn't need to be complicated",
                    count=random.choice(["5", "7", "10"]),
                    event=f"our {niche} journey",
                ),
                "hashtags": [f"#{niche.replace(' ', '')}", "#ContentCreation", "#GrowthHacking"],
                "status": "planned",
            })
    
    return calendar


def generate_calendar_ai(niche: str, weeks: int, platforms: list[str], posts_per_week: int) -> list[dict]:
    """Generate calendar with AI-powered content ideas."""
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("No API key")
        
        client = OpenAI(api_key=api_key)
        total_posts = weeks * posts_per_week
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": f"Generate {total_posts} social media post ideas for the niche: {niche}. "
                           f"Platforms: {', '.join(platforms)}. "
                           f"Return JSON array with objects having: type, idea, hashtags (array), platform. "
                           f"Mix educational, entertaining, and promotional content. Be specific and creative."
            }],
            max_tokens=3000,
            response_format={"type": "json_object"},
        )
        
        data = json.loads(resp.choices[0].message.content)
        posts = data.get("posts", data.get("ideas", []))
        
        # Add dates
        start_date = datetime.now()
        post_days = [0, 2, 4] if posts_per_week <= 3 else list(range(5))
        
        calendar = []
        for i, post in enumerate(posts[:total_posts]):
            week = i // posts_per_week
            day_in_week = i % posts_per_week
            day_offset = post_days[day_in_week % len(post_days)]
            post_date = start_date + timedelta(weeks=week, days=day_offset)
            platform = post.get("platform", random.choice(platforms))
            
            calendar.append({
                "date": post_date.strftime("%Y-%m-%d"),
                "day": post_date.strftime("%A"),
                "time": random.choice(BEST_TIMES.get(platform, ["12:00 PM"])),
                "platform": platform,
                "type": post.get("type", "General"),
                "idea": post.get("idea", ""),
                "hashtags": post.get("hashtags", []),
                "status": "planned",
            })
        
        return calendar
    except Exception as e:
        print(f"AI generation failed: {e}. Using templates.", file=sys.stderr)
        return generate_calendar_template(niche, weeks, platforms, posts_per_week)


def format_markdown(calendar: list[dict]) -> str:
    """Format calendar as Markdown."""
    lines = ["# Content Calendar\n"]
    
    current_week = ""
    for post in calendar:
        week_label = f"Week of {post['date'][:10]}"
        # Simple week grouping
        week_num = datetime.strptime(post["date"], "%Y-%m-%d").isocalendar()[1]
        if f"Week {week_num}" != current_week:
            current_week = f"Week {week_num}"
            lines.append(f"\n## {current_week}\n")
        
        lines.append(f"### {post['day']}, {post['date']} — {post['time']}")
        lines.append(f"**Platform:** {post['platform']}  ")
        lines.append(f"**Type:** {post.get('emoji', '📝')} {post['type']}  ")
        lines.append(f"**Idea:** {post['idea']}  ")
        if post.get("hashtags"):
            lines.append(f"**Hashtags:** {' '.join(post['hashtags'])}  ")
        lines.append(f"**Status:** {post['status']}")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate content calendar")
    parser.add_argument("--niche", required=True, help="Content niche/topic")
    parser.add_argument("--weeks", type=int, default=4, help="Weeks to plan (default: 4)")
    parser.add_argument("--platforms", default="twitter,linkedin", help="Platforms (comma-separated)")
    parser.add_argument("--posts-per-week", type=int, default=3, help="Posts per week (default: 3)")
    parser.add_argument("--ai", action="store_true", help="Use AI for content ideas")
    parser.add_argument("--output", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()
    
    platforms = [p.strip() for p in args.platforms.split(",")]
    
    if args.ai:
        calendar = generate_calendar_ai(args.niche, args.weeks, platforms, args.posts_per_week)
    else:
        calendar = generate_calendar_template(args.niche, args.weeks, platforms, args.posts_per_week)
    
    if args.output == "json":
        print(json.dumps(calendar, indent=2))
    else:
        print(format_markdown(calendar))


if __name__ == "__main__":
    main()
