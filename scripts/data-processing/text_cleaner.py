#!/usr/bin/env python3
"""
Text Cleaner — Clean and normalize messy text data.

Remove HTML tags, fix encoding, normalize whitespace, strip URLs/emails,
and apply custom regex filters. Useful for preprocessing data pipelines.

Usage:
    python text_cleaner.py input.txt
    python text_cleaner.py --text "messy   text  <b>here</b>" --strip-html --normalize
    python text_cleaner.py input.csv --field description --output clean.csv
    cat messy.txt | python text_cleaner.py --stdin --strip-urls --strip-emails

No external dependencies required.
"""

import argparse
import csv
import html
import json
import re
import sys
import unicodedata


def strip_html(text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    return text


def normalize_whitespace(text):
    """Collapse multiple spaces/newlines into single space."""
    text = re.sub(r'[\t ]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def strip_urls(text):
    return re.sub(r'https?://\S+', '', text)


def strip_emails(text):
    return re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '', text)


def strip_emojis(text):
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub('', text)


def normalize_unicode(text):
    """Normalize unicode characters (e.g., smart quotes → straight quotes)."""
    text = unicodedata.normalize('NFKD', text)
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '--', '\u2026': '...', '\u00a0': ' ',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def strip_numbers(text):
    return re.sub(r'\b\d+\b', '', text)


def lowercase(text):
    return text.lower()


def clean_text(text, operations):
    """Apply cleaning operations in order."""
    ops = {
        'html': strip_html,
        'whitespace': normalize_whitespace,
        'urls': strip_urls,
        'emails': strip_emails,
        'emojis': strip_emojis,
        'unicode': normalize_unicode,
        'numbers': strip_numbers,
        'lowercase': lowercase,
    }
    
    for op in operations:
        if op in ops:
            text = ops[op](text)
    
    return text


def process_file(input_path, field=None, operations=None, output_path=None):
    """Process a text or CSV file."""
    operations = operations or ['html', 'whitespace', 'unicode']
    
    if input_path.endswith('.csv') and field:
        with open(input_path, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames
        
        for row in rows:
            if field in row:
                row[field] = clean_text(row[field], operations)
        
        out = output_path or sys.stdout
        if isinstance(out, str):
            out = open(out, 'w', newline='')
        
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
        if output_path:
            out.close()
            print(f"✅ Cleaned {len(rows)} rows → {output_path}", file=sys.stderr)
    else:
        with open(input_path) as f:
            text = f.read()
        
        cleaned = clean_text(text, operations)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(cleaned)
            print(f"✅ Cleaned → {output_path}", file=sys.stderr)
        else:
            print(cleaned)


def main():
    parser = argparse.ArgumentParser(description="Clean and normalize text data")
    parser.add_argument("input", nargs="?", help="Input file")
    parser.add_argument("--text", help="Direct text input")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--field", help="CSV field to clean")
    parser.add_argument("--output", "-o", help="Output file")
    
    parser.add_argument("--strip-html", action="store_true")
    parser.add_argument("--normalize", action="store_true", help="Normalize whitespace")
    parser.add_argument("--strip-urls", action="store_true")
    parser.add_argument("--strip-emails", action="store_true")
    parser.add_argument("--strip-emojis", action="store_true")
    parser.add_argument("--strip-numbers", action="store_true")
    parser.add_argument("--normalize-unicode", action="store_true")
    parser.add_argument("--lowercase", action="store_true")
    parser.add_argument("--all", action="store_true", help="Apply all cleaners")
    args = parser.parse_args()
    
    operations = []
    if args.all:
        operations = ['html', 'urls', 'emails', 'emojis', 'unicode', 'numbers', 'lowercase', 'whitespace']
    else:
        if args.strip_html: operations.append('html')
        if args.strip_urls: operations.append('urls')
        if args.strip_emails: operations.append('emails')
        if args.strip_emojis: operations.append('emojis')
        if args.normalize_unicode: operations.append('unicode')
        if args.strip_numbers: operations.append('numbers')
        if args.lowercase: operations.append('lowercase')
        if args.normalize or not operations: operations.append('whitespace')
    
    if args.text:
        print(clean_text(args.text, operations))
    elif args.stdin or (not args.input and not sys.stdin.isatty()):
        print(clean_text(sys.stdin.read(), operations))
    elif args.input:
        process_file(args.input, args.field, operations, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
