#!/usr/bin/env python3
"""
Structured Data Extractor
=========================
Extract structured data from unstructured text using LLMs.
Define a schema, feed in text, get clean JSON back.

Usage:
    python structured_extractor.py --schema schema.json --input emails.txt
    python structured_extractor.py --schema '{"name":"str","email":"str","company":"str"}' --input leads.txt
    cat resume.pdf | python structured_extractor.py --schema resume_schema.json

Environment:
    OPENAI_API_KEY or ANTHROPIC_API_KEY
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


EXAMPLE_SCHEMAS = {
    "contact": {
        "name": "string — full name",
        "email": "string — email address",
        "phone": "string — phone number",
        "company": "string — company name",
        "role": "string — job title or role",
    },
    "invoice": {
        "vendor": "string — company issuing the invoice",
        "invoice_number": "string",
        "date": "string — YYYY-MM-DD",
        "items": [{"description": "string", "quantity": "number", "unit_price": "number"}],
        "total": "number",
        "currency": "string — ISO 4217 code",
    },
    "event": {
        "title": "string — event name",
        "date": "string — YYYY-MM-DD",
        "time": "string — HH:MM",
        "location": "string",
        "description": "string — brief description",
        "attendees": ["string — names"],
    },
}


def extract_with_openai(text: str, schema: dict, api_key: str) -> dict:
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Extract structured data from the input text. "
                            "Return ONLY valid JSON matching the schema. "
                            "If a field is not found, use null. "
                            f"Schema: {json.dumps(schema)}"
                        ),
                    },
                    {"role": "user", "content": text[:10000]},
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 2000,
            },
        )
        resp.raise_for_status()
        return json.loads(resp.json()["choices"][0]["message"]["content"])


def extract_with_anthropic(text: str, schema: dict, api_key: str) -> dict:
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Extract structured data from this text. Return ONLY valid JSON matching this schema:\n"
                            f"{json.dumps(schema, indent=2)}\n\n"
                            f"If a field is not found, use null.\n\nText:\n{text[:10000]}"
                        ),
                    }
                ],
            },
        )
        resp.raise_for_status()
        raw = resp.json()["content"][0]["text"]
        # Handle potential markdown wrapping
        if "```" in raw:
            import re
            match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
            if match:
                raw = match.group(1)
        return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured data from text using AI",
        epilog="Built-in schemas: contact, invoice, event",
    )
    parser.add_argument("--input", help="Input file (or pipe via stdin)")
    parser.add_argument("--schema", required=True, help="JSON schema file, inline JSON, or built-in name")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")
    parser.add_argument("--batch", action="store_true", help="Process each paragraph separately")
    parser.add_argument("--list-schemas", action="store_true", help="List built-in schemas")
    args = parser.parse_args()

    if args.list_schemas:
        for name, schema in EXAMPLE_SCHEMAS.items():
            print(f"\n📋 {name}:")
            print(json.dumps(schema, indent=2))
        return

    # Load schema
    if args.schema in EXAMPLE_SCHEMAS:
        schema = EXAMPLE_SCHEMAS[args.schema]
    elif args.schema.startswith("{"):
        schema = json.loads(args.schema)
    else:
        schema = json.loads(Path(args.schema).read_text())

    # Load text
    if args.input:
        text = Path(args.input).read_text(encoding="utf-8", errors="replace")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("Provide --input or pipe text via stdin")
        sys.exit(1)

    # Get API key
    env_key = "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
    api_key = os.environ.get(env_key)
    if not api_key:
        print(f"Error: Set {env_key}")
        sys.exit(1)

    extract = extract_with_openai if args.provider == "openai" else extract_with_anthropic

    # Process
    if args.batch:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        results = []
        for i, para in enumerate(paragraphs):
            print(f"  Processing {i+1}/{len(paragraphs)}...", file=sys.stderr)
            try:
                results.append(extract(para, schema, api_key))
            except Exception as e:
                print(f"  ⚠ Error on paragraph {i+1}: {e}", file=sys.stderr)
                results.append({"error": str(e), "input": para[:100]})
        output = results
    else:
        output = extract(text, schema, api_key)

    # Output
    result_json = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(result_json)
        print(f"✅ Extracted → {args.output}", file=sys.stderr)
    else:
        print(result_json)


if __name__ == "__main__":
    main()
