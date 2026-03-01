#!/usr/bin/env python3
"""
AI Translation Tool — Translate text or files between languages.

Supports batch translation of files, with context-aware translation
that preserves formatting and technical terminology.

Usage:
    python translation_tool.py --text "Hello world" --to es
    python translation_tool.py --input docs/README.md --to ru --output docs/README_ru.md
    python translation_tool.py --text "API endpoint returns 403" --to ja --preserve-technical

Requirements:
    pip install openai
"""

import argparse
import json
import os
import sys

try:
    from openai import OpenAI
except ImportError:
    print("Install openai: pip install openai", file=sys.stderr)
    sys.exit(1)

LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ja": "Japanese",
    "ko": "Korean", "zh": "Chinese", "ar": "Arabic", "hi": "Hindi",
    "nl": "Dutch", "pl": "Polish", "sv": "Swedish", "tr": "Turkish",
    "uk": "Ukrainian", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian",
}


def translate(text: str, target_lang: str, source_lang: str = "auto",
              preserve_technical: bool = False, context: str = "",
              client: OpenAI = None, model: str = "gpt-4o-mini") -> dict:
    """Translate text to target language."""
    target = LANGUAGES.get(target_lang, target_lang)
    source = LANGUAGES.get(source_lang, source_lang) if source_lang != "auto" else "the source language"
    
    system_prompt = f"You are a professional translator. Translate from {source} to {target}."
    if preserve_technical:
        system_prompt += " Keep technical terms (API names, code, URLs, variable names) in their original form."
    if context:
        system_prompt += f" Context: {context}"
    system_prompt += " Respond with JSON: {\"translated\": \"...\", \"source_language\": \"detected language\"}"
    
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text[:6000]},
        ],
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    
    try:
        result = json.loads(resp.choices[0].message.content)
        return result
    except json.JSONDecodeError:
        return {"translated": resp.choices[0].message.content, "source_language": "unknown"}


def main():
    parser = argparse.ArgumentParser(description="AI-powered translation")
    parser.add_argument("--text", help="Text to translate")
    parser.add_argument("--input", "-i", help="Input file")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--to", required=True, help="Target language code (e.g., es, fr, ja)")
    parser.add_argument("--from", dest="source", default="auto", help="Source language (default: auto)")
    parser.add_argument("--preserve-technical", action="store_true")
    parser.add_argument("--context", default="", help="Extra context for translation")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--list-languages", action="store_true")
    args = parser.parse_args()
    
    if args.list_languages:
        for code, name in sorted(LANGUAGES.items()):
            print(f"  {code}: {name}")
        return
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    
    if args.input:
        with open(args.input) as f:
            text = f.read()
    elif args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.error("Provide --text, --input, or pipe via stdin")
    
    result = translate(text, args.to, args.source, args.preserve_technical,
                      args.context, client, args.model)
    
    translated = result.get("translated", "")
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(translated)
        print(f"✅ Translated to {LANGUAGES.get(args.to, args.to)} → {args.output}")
        print(f"   Source: {result.get('source_language', 'unknown')}")
    else:
        print(translated)


if __name__ == "__main__":
    main()
