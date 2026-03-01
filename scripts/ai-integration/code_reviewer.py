#!/usr/bin/env python3
"""
AI Code Reviewer — Review code files or git diffs with AI feedback.

Provides actionable code review feedback: bugs, style issues, security
concerns, and improvement suggestions.

Usage:
    python code_reviewer.py myfile.py
    python code_reviewer.py --diff                   # Review staged changes
    python code_reviewer.py --pr 42                  # Review a PR (requires gh CLI)
    python code_reviewer.py --dir src/ --pattern "*.py" --focus security

Requirements:
    pip install openai
"""

import argparse
import glob
import json
import os
import subprocess
import sys

try:
    from openai import OpenAI
except ImportError:
    print("Install openai: pip install openai", file=sys.stderr)
    sys.exit(1)


def get_git_diff(staged: bool = True) -> str:
    """Get git diff for staged or unstaged changes."""
    cmd = ["git", "diff", "--cached"] if staged else ["git", "diff"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def get_pr_diff(pr_number: int) -> str:
    """Get PR diff using gh CLI."""
    result = subprocess.run(
        ["gh", "pr", "diff", str(pr_number)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Error getting PR diff: {result.stderr}", file=sys.stderr)
        return ""
    return result.stdout


def review_code(code: str, filename: str, focus: str, client: OpenAI,
                model: str = "gpt-4o-mini") -> dict:
    """Review code with AI."""
    focus_prompts = {
        "general": "Provide a comprehensive code review.",
        "security": "Focus on security vulnerabilities: injection, auth issues, data exposure, insecure defaults.",
        "performance": "Focus on performance issues: inefficient algorithms, unnecessary allocations, N+1 queries.",
        "style": "Focus on code style: naming, structure, readability, best practices.",
        "bugs": "Focus on potential bugs: edge cases, type errors, race conditions, off-by-one errors.",
    }
    
    focus_instruction = focus_prompts.get(focus, focus_prompts["general"])
    
    resp = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "system",
            "content": f"You are an expert code reviewer. {focus_instruction}\n"
                       f"Provide feedback as JSON with:\n"
                       f"- issues: array of {{severity: 'critical'|'warning'|'info', line: number|null, description: string, suggestion: string}}\n"
                       f"- summary: brief overall assessment\n"
                       f"- score: 1-10 quality score"
        }, {
            "role": "user",
            "content": f"File: {filename}\n\n```\n{code[:8000]}\n```"
        }],
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    
    try:
        result = json.loads(resp.choices[0].message.content)
        result["filename"] = filename
        return result
    except json.JSONDecodeError:
        return {"filename": filename, "summary": resp.choices[0].message.content, "issues": [], "score": 0}


def format_review(review: dict) -> str:
    """Format review as readable text."""
    lines = [f"\n📝 Review: {review['filename']}"]
    lines.append(f"Score: {'⭐' * review.get('score', 0)}/{'⭐' * 10} ({review.get('score', '?')}/10)")
    lines.append(f"Summary: {review.get('summary', 'N/A')}\n")
    
    icons = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
    
    issues = review.get("issues", [])
    if issues:
        lines.append(f"Issues ({len(issues)}):")
        for issue in issues:
            icon = icons.get(issue.get("severity", "info"), "🔵")
            line_ref = f" (line {issue['line']})" if issue.get("line") else ""
            lines.append(f"  {icon} [{issue.get('severity', 'info').upper()}]{line_ref}")
            lines.append(f"     {issue.get('description', '')}")
            if issue.get("suggestion"):
                lines.append(f"     💡 {issue['suggestion']}")
    else:
        lines.append("✅ No issues found!")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AI code reviewer")
    parser.add_argument("files", nargs="*", help="Files to review")
    parser.add_argument("--diff", action="store_true", help="Review git staged changes")
    parser.add_argument("--unstaged", action="store_true", help="Review unstaged changes")
    parser.add_argument("--pr", type=int, help="Review a PR by number")
    parser.add_argument("--dir", help="Review all matching files in directory")
    parser.add_argument("--pattern", default="*.py", help="File pattern for --dir")
    parser.add_argument("--focus", default="general",
                       choices=["general", "security", "performance", "style", "bugs"])
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    reviews = []
    
    if args.diff or args.unstaged:
        diff = get_git_diff(staged=not args.unstaged)
        if diff:
            review = review_code(diff, "git diff", args.focus, client, args.model)
            reviews.append(review)
        else:
            print("No changes to review.")
    
    elif args.pr:
        diff = get_pr_diff(args.pr)
        if diff:
            review = review_code(diff, f"PR #{args.pr}", args.focus, client, args.model)
            reviews.append(review)
    
    elif args.dir:
        files = glob.glob(os.path.join(args.dir, "**", args.pattern), recursive=True)
        for fpath in files[:20]:  # Limit to 20 files
            with open(fpath) as f:
                code = f.read()
            review = review_code(code, fpath, args.focus, client, args.model)
            reviews.append(review)
    
    else:
        for fpath in (args.files or []):
            with open(fpath) as f:
                code = f.read()
            review = review_code(code, fpath, args.focus, client, args.model)
            reviews.append(review)
    
    if not reviews:
        parser.print_help()
        return
    
    if args.json:
        print(json.dumps(reviews, indent=2))
    else:
        for review in reviews:
            print(format_review(review))


if __name__ == "__main__":
    main()
