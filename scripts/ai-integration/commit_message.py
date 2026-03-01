#!/usr/bin/env python3
"""
AI Commit Message Generator — Generate conventional commit messages from diffs.

Analyzes staged git changes and generates descriptive commit messages
following conventional commit format.

Usage:
    python commit_message.py                    # Generate from staged changes
    python commit_message.py --apply            # Generate and commit directly
    python commit_message.py --style angular    # Angular convention style

Requirements:
    pip install openai
"""

import argparse
import json
import os
import subprocess
import sys

try:
    from openai import OpenAI
except ImportError:
    print("Install openai: pip install openai", file=sys.stderr)
    sys.exit(1)

STYLES = {
    "conventional": "type(scope): description\n\nOptional body with details.",
    "angular": "type(scope): short description\n\nBREAKING CHANGE: ...",
    "simple": "Short descriptive message",
    "detailed": "type: description\n\n- bullet point changes\n- another change",
}


def get_staged_diff():
    result = subprocess.run(["git", "diff", "--cached", "--stat"], capture_output=True, text=True)
    stat = result.stdout
    
    result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True)
    diff = result.stdout
    
    if not diff:
        print("No staged changes. Stage changes with: git add <files>", file=sys.stderr)
        sys.exit(1)
    
    return stat, diff


def generate_message(diff, stat, style="conventional", model="gpt-4o-mini"):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    
    style_desc = STYLES.get(style, STYLES["conventional"])
    
    resp = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "system",
            "content": f"Generate a git commit message for the following changes. "
                       f"Style: {style_desc}\n"
                       f"Types: feat, fix, docs, style, refactor, test, chore, perf, ci\n"
                       f"Be specific but concise. First line max 72 chars."
        }, {
            "role": "user",
            "content": f"Stats:\n{stat}\n\nDiff (truncated):\n{diff[:4000]}"
        }],
        max_tokens=300,
    )
    
    return resp.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser(description="Generate commit messages with AI")
    parser.add_argument("--style", choices=STYLES.keys(), default="conventional")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--apply", action="store_true", help="Commit with generated message")
    parser.add_argument("--count", type=int, default=3, help="Number of suggestions")
    args = parser.parse_args()
    
    stat, diff = get_staged_diff()
    
    print("📊 Changes:", file=sys.stderr)
    print(stat, file=sys.stderr)
    
    messages = []
    for i in range(args.count):
        msg = generate_message(diff, stat, args.style, args.model)
        messages.append(msg)
    
    print("💬 Suggested commit messages:\n")
    for i, msg in enumerate(messages, 1):
        print(f"  [{i}] {msg}\n")
    
    if args.apply:
        choice = input(f"Apply which message? (1-{len(messages)}, or 'n' to cancel): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(messages):
            msg = messages[int(choice) - 1]
            subprocess.run(["git", "commit", "-m", msg])
            print(f"✅ Committed with message: {msg.split(chr(10))[0]}")
        else:
            print("Cancelled.")


if __name__ == "__main__":
    main()
