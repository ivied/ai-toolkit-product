#!/usr/bin/env python3
"""
Dedup Tool — Find and remove duplicate files, lines, or records.

Detects duplicates by content hash (files), exact match (lines),
or fuzzy match (records by key fields).

Usage:
    python dedup_tool.py files ~/Downloads               # Find duplicate files
    python dedup_tool.py lines input.txt                 # Remove duplicate lines
    python dedup_tool.py records data.json --key email   # Dedup JSON by field
    python dedup_tool.py files ~/Photos --delete         # Delete duplicates (keep first)

No external dependencies required.
"""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def hash_file(path: str, chunk_size: int = 8192) -> str:
    """Hash file content."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def find_duplicate_files(directory: str, min_size: int = 0, extensions: list = None) -> dict:
    """Find duplicate files in a directory."""
    # Group by size first (fast pre-filter)
    by_size = defaultdict(list)
    
    for root, dirs, files in os.walk(directory):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                size = os.path.getsize(fpath)
                if size < min_size:
                    continue
                if extensions:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in extensions:
                        continue
                by_size[size].append(fpath)
            except (OSError, PermissionError):
                continue
    
    # Hash only files with same size
    duplicates = defaultdict(list)
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        for path in paths:
            try:
                file_hash = hash_file(path)
                duplicates[file_hash].append(path)
            except (OSError, PermissionError):
                continue
    
    # Filter to only actual duplicates
    return {h: paths for h, paths in duplicates.items() if len(paths) > 1}


def dedup_lines(input_path: str, output_path: str = None, preserve_order: bool = True) -> dict:
    """Remove duplicate lines from a file."""
    with open(input_path) as f:
        lines = f.readlines()
    
    seen = set()
    unique = []
    duplicates = 0
    
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped in seen:
            duplicates += 1
        else:
            seen.add(stripped)
            unique.append(line)
    
    if output_path:
        with open(output_path, "w") as f:
            f.writelines(unique)
    else:
        sys.stdout.writelines(unique)
    
    return {
        "total_lines": len(lines),
        "unique_lines": len(unique),
        "duplicates_removed": duplicates,
    }


def dedup_records(input_path: str, key_field: str, output_path: str = None) -> dict:
    """Remove duplicate records from JSON by key field."""
    with open(input_path) as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        print("Error: expected JSON array", file=sys.stderr)
        return {}
    
    seen = set()
    unique = []
    duplicates = 0
    
    for record in data:
        key_value = str(record.get(key_field, ""))
        if key_value in seen:
            duplicates += 1
        else:
            seen.add(key_value)
            unique.append(record)
    
    result = json.dumps(unique, indent=2, ensure_ascii=False)
    if output_path:
        with open(output_path, "w") as f:
            f.write(result)
    else:
        print(result)
    
    return {
        "total_records": len(data),
        "unique_records": len(unique),
        "duplicates_removed": duplicates,
        "key_field": key_field,
    }


def _human_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main():
    parser = argparse.ArgumentParser(description="Find and remove duplicates")
    sub = parser.add_subparsers(dest="command")
    
    fp = sub.add_parser("files", help="Find duplicate files")
    fp.add_argument("directory")
    fp.add_argument("--min-size", type=int, default=0, help="Min file size in bytes")
    fp.add_argument("--extensions", help="Comma-separated extensions (e.g., .jpg,.png)")
    fp.add_argument("--delete", action="store_true", help="Delete duplicates (keep first)")
    fp.add_argument("--json", action="store_true")
    
    lp = sub.add_parser("lines", help="Remove duplicate lines")
    lp.add_argument("input"); lp.add_argument("--output", "-o")
    
    rp = sub.add_parser("records", help="Dedup JSON records")
    rp.add_argument("input"); rp.add_argument("--key", required=True)
    rp.add_argument("--output", "-o")
    
    args = parser.parse_args()
    
    if args.command == "files":
        exts = [e.strip() if e.startswith(".") else f".{e.strip()}"
                for e in args.extensions.split(",")] if args.extensions else None
        
        dupes = find_duplicate_files(args.directory, args.min_size, exts)
        
        if args.json:
            print(json.dumps(dupes, indent=2))
        else:
            total_waste = 0
            for h, paths in dupes.items():
                size = os.path.getsize(paths[0])
                waste = size * (len(paths) - 1)
                total_waste += waste
                print(f"\n🔄 Duplicate group ({_human_size(size)} each, {len(paths)} copies):")
                for i, p in enumerate(paths):
                    marker = "  ✅ KEEP " if i == 0 else "  ❌ DUP  "
                    print(f"{marker} {p}")
                    
                    if args.delete and i > 0:
                        os.remove(p)
                        print(f"         → Deleted")
            
            n_groups = len(dupes)
            n_files = sum(len(p) - 1 for p in dupes.values())
            print(f"\n{'='*50}")
            print(f"Found {n_groups} duplicate groups, {n_files} duplicate files")
            print(f"Wasted space: {_human_size(total_waste)}")
            if args.delete:
                print(f"Freed: {_human_size(total_waste)}")
    
    elif args.command == "lines":
        stats = dedup_lines(args.input, args.output)
        print(f"\nLines: {stats['total_lines']} → {stats['unique_lines']} "
              f"({stats['duplicates_removed']} removed)", file=sys.stderr)
    
    elif args.command == "records":
        stats = dedup_records(args.input, args.key, args.output)
        if stats:
            print(f"\nRecords: {stats['total_records']} → {stats['unique_records']} "
                  f"({stats['duplicates_removed']} removed by {stats['key_field']})", file=sys.stderr)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
