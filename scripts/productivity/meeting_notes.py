#!/usr/bin/env python3
"""
Meeting Notes Generator — Structure meeting notes with AI or templates.

Takes raw meeting notes/transcript and generates structured output with
action items, decisions, and follow-ups.

Usage:
    python meeting_notes.py --input raw_notes.txt
    python meeting_notes.py --input transcript.txt --ai
    echo "Meeting notes..." | python meeting_notes.py --stdin
    python meeting_notes.py --template standup

Requirements:
    pip install openai  (optional, for AI summarization)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

TEMPLATES = {
    "standup": {
        "title": "Daily Standup",
        "sections": ["Yesterday", "Today", "Blockers"],
    },
    "general": {
        "title": "Meeting Notes",
        "sections": ["Discussion", "Decisions", "Action Items", "Next Steps"],
    },
    "retrospective": {
        "title": "Retrospective",
        "sections": ["What Went Well", "What Didn't Go Well", "Action Items"],
    },
    "planning": {
        "title": "Planning Session",
        "sections": ["Goals", "Tasks", "Assignments", "Timeline", "Dependencies"],
    },
    "one_on_one": {
        "title": "1:1 Meeting",
        "sections": ["Updates", "Challenges", "Feedback", "Goals", "Action Items"],
    },
}


def extract_action_items(text: str) -> list[str]:
    """Extract action items from raw text."""
    patterns = [
        r'(?:TODO|ACTION|TASK|AI)[\s:]+(.+)',
        r'(?:need to|should|will|must|going to)\s+(.+?)(?:\.|$)',
        r'@(\w+)\s+(?:to|will|should)\s+(.+?)(?:\.|$)',
    ]
    
    items = []
    for line in text.split("\n"):
        line = line.strip()
        for pattern in patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                item = match if isinstance(match, str) else " ".join(match)
                item = item.strip().rstrip(".")
                if len(item) > 5 and item not in items:
                    items.append(item)
    
    return items


def extract_decisions(text: str) -> list[str]:
    """Extract decisions from raw text."""
    patterns = [
        r'(?:decided|agreed|decision|resolved)[\s:]+(.+?)(?:\.|$)',
        r'(?:we\'ll go with|going with|chose|selected)\s+(.+?)(?:\.|$)',
    ]
    
    decisions = []
    for line in text.split("\n"):
        for pattern in patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                match = match.strip().rstrip(".")
                if len(match) > 5 and match not in decisions:
                    decisions.append(match)
    
    return decisions


def structure_notes(raw_text: str, template: str = "general") -> dict:
    """Structure raw notes using pattern extraction."""
    tmpl = TEMPLATES.get(template, TEMPLATES["general"])
    
    action_items = extract_action_items(raw_text)
    decisions = extract_decisions(raw_text)
    
    # Split text into paragraphs
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    
    # Try to match paragraphs to sections
    sections = {}
    for section in tmpl["sections"]:
        sections[section] = []
    
    current_section = tmpl["sections"][0] if tmpl["sections"] else "Notes"
    for para in paragraphs:
        # Check if paragraph matches a section header
        for section in tmpl["sections"]:
            if section.lower() in para.lower()[:50]:
                current_section = section
                para = re.sub(rf'^.*{section}.*$', '', para, flags=re.IGNORECASE | re.MULTILINE).strip()
                break
        
        if para:
            if current_section not in sections:
                sections[current_section] = []
            sections[current_section].append(para)
    
    return {
        "title": tmpl["title"],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "template": template,
        "sections": sections,
        "action_items": action_items,
        "decisions": decisions,
        "raw_length": len(raw_text),
    }


def structure_notes_ai(raw_text: str, template: str = "general") -> dict:
    """Use AI to structure notes."""
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("No OPENAI_API_KEY")
        
        client = OpenAI(api_key=api_key)
        tmpl = TEMPLATES.get(template, TEMPLATES["general"])
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": f"Structure these meeting notes into a clear format. "
                           f"Sections: {', '.join(tmpl['sections'])}. "
                           f"Also extract: action items (with assignees if mentioned), "
                           f"decisions made, and key discussion points. "
                           f"Return as JSON with keys: sections (dict), action_items (list), decisions (list)."
            }, {
                "role": "user",
                "content": raw_text[:6000]
            }],
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        
        data = json.loads(resp.choices[0].message.content)
        data["title"] = tmpl["title"]
        data["date"] = datetime.now().strftime("%Y-%m-%d")
        data["template"] = template
        return data
    except Exception as e:
        print(f"AI structuring failed: {e}. Using pattern extraction.", file=sys.stderr)
        return structure_notes(raw_text, template)


def format_markdown(notes: dict) -> str:
    """Format structured notes as Markdown."""
    lines = [f"# {notes['title']} — {notes['date']}\n"]
    
    for section, content in notes.get("sections", {}).items():
        lines.append(f"## {section}\n")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    lines.append(f"- {item}")
                else:
                    lines.append(f"- {json.dumps(item)}")
        elif isinstance(content, str):
            lines.append(content)
        lines.append("")
    
    if notes.get("action_items"):
        lines.append("## ✅ Action Items\n")
        for item in notes["action_items"]:
            lines.append(f"- [ ] {item}")
        lines.append("")
    
    if notes.get("decisions"):
        lines.append("## 📋 Decisions\n")
        for decision in notes["decisions"]:
            lines.append(f"- ✓ {decision}")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Structure meeting notes")
    parser.add_argument("--input", help="Input file with raw notes")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--template", choices=list(TEMPLATES.keys()), default="general")
    parser.add_argument("--ai", action="store_true", help="Use AI for structuring")
    parser.add_argument("--output", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--list-templates", action="store_true", help="List templates")
    args = parser.parse_args()
    
    if args.list_templates:
        for name, tmpl in TEMPLATES.items():
            print(f"  {name}: {tmpl['title']} — Sections: {', '.join(tmpl['sections'])}")
        return
    
    if args.input:
        with open(args.input) as f:
            raw_text = f.read()
    elif args.stdin or not sys.stdin.isatty():
        raw_text = sys.stdin.read()
    else:
        parser.error("Provide --input or pipe via stdin")
    
    if args.ai:
        notes = structure_notes_ai(raw_text, args.template)
    else:
        notes = structure_notes(raw_text, args.template)
    
    if args.output == "json":
        print(json.dumps(notes, indent=2, ensure_ascii=False))
    else:
        print(format_markdown(notes))


if __name__ == "__main__":
    main()
