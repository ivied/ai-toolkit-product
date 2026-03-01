#!/usr/bin/env python3
"""
Text Classifier — Classify text into categories using AI.

Categorizes support tickets, reviews, emails, or any text into
user-defined categories using OpenAI or Anthropic APIs.

Usage:
    python text_classifier.py --text "My order arrived broken" --categories "complaint,inquiry,praise,bug"
    python text_classifier.py --input emails.json --categories "urgent,routine,spam" --output results.json
    python text_classifier.py --input feedback.csv --field "comment" --categories "positive,negative,neutral"

Requirements:
    pip install openai
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Install openai: pip install openai", file=sys.stderr)
    sys.exit(1)


def classify_text(text: str, categories: list[str], client: OpenAI, model: str = "gpt-4o-mini") -> dict:
    """Classify a single text into one of the given categories."""
    resp = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "system",
            "content": f"You are a text classifier. Classify the given text into exactly one of these categories: {', '.join(categories)}. "
                       f"Respond with JSON: {{\"category\": \"chosen_category\", \"confidence\": 0.0-1.0, \"reasoning\": \"brief explanation\"}}"
        }, {
            "role": "user",
            "content": text[:2000]
        }],
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    
    try:
        result = json.loads(resp.choices[0].message.content)
        result["text_preview"] = text[:100]
        return result
    except json.JSONDecodeError:
        return {"category": "unknown", "confidence": 0, "text_preview": text[:100]}


def classify_batch(items: list[dict], text_field: str, categories: list[str],
                   client: OpenAI, model: str = "gpt-4o-mini") -> list[dict]:
    """Classify a batch of items."""
    results = []
    total = len(items)
    
    for i, item in enumerate(items, 1):
        text = item.get(text_field, "")
        if not text:
            results.append({**item, "_category": "empty", "_confidence": 0})
            continue
        
        print(f"  Classifying {i}/{total}...", end="\r", file=sys.stderr)
        
        result = classify_text(text, categories, client, model)
        results.append({
            **item,
            "_category": result.get("category", "unknown"),
            "_confidence": result.get("confidence", 0),
            "_reasoning": result.get("reasoning", ""),
        })
    
    print(f"  Classified {total}/{total} items.", file=sys.stderr)
    return results


def main():
    parser = argparse.ArgumentParser(description="AI-powered text classifier")
    parser.add_argument("--text", help="Single text to classify")
    parser.add_argument("--input", help="Input file (JSON or CSV)")
    parser.add_argument("--field", default="text", help="Field name containing text (for batch)")
    parser.add_argument("--categories", required=True, help="Comma-separated categories")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    args = parser.parse_args()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    categories = [c.strip() for c in args.categories.split(",")]
    
    if args.text:
        result = classify_text(args.text, categories, client, args.model)
        print(json.dumps(result, indent=2))
    
    elif args.input:
        ext = Path(args.input).suffix.lower()
        if ext == ".csv":
            with open(args.input, newline="") as f:
                items = list(csv.DictReader(f))
        else:
            with open(args.input) as f:
                items = json.load(f)
                if not isinstance(items, list):
                    items = [items]
        
        results = classify_batch(items, args.field, categories, client, args.model)
        
        # Summary
        from collections import Counter
        cats = Counter(r.get("_category", "unknown") for r in results)
        print(f"\n📊 Classification Summary:", file=sys.stderr)
        for cat, count in cats.most_common():
            pct = count / len(results) * 100
            print(f"  {cat}: {count} ({pct:.1f}%)", file=sys.stderr)
        
        output = json.dumps(results, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"\n✅ Results saved to {args.output}", file=sys.stderr)
        else:
            print(output)
    else:
        parser.error("Provide --text or --input")


if __name__ == "__main__":
    main()
