#!/usr/bin/env python3
"""
CSV Toolkit
===========
Swiss-army knife for CSV operations. No pandas required.

Usage:
    python csv_toolkit.py info data.csv                         # Show stats
    python csv_toolkit.py filter data.csv "age > 30"            # Filter rows
    python csv_toolkit.py select data.csv name,email            # Select columns
    python csv_toolkit.py sort data.csv --by revenue --desc     # Sort
    python csv_toolkit.py dedup data.csv --by email             # Remove duplicates
    python csv_toolkit.py merge a.csv b.csv --on id             # Join files
    python csv_toolkit.py convert data.csv --to json            # Convert format
    python csv_toolkit.py split data.csv --by country --output chunks/
"""

import argparse
import csv
import json
import operator
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def read_csv(filepath: str) -> tuple[list[str], list[dict]]:
    """Read CSV and return (headers, rows as dicts)."""
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def write_csv(filepath: str, headers: list[str], rows: list[dict]):
    """Write rows to CSV."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def parse_condition(condition: str):
    """Parse a simple condition like 'age > 30' or 'status == active'."""
    ops = {
        ">=": operator.ge, "<=": operator.le, "!=": operator.ne,
        ">": operator.gt, "<": operator.lt, "==": operator.eq, "=": operator.eq,
        "contains": lambda a, b: b.lower() in a.lower(),
    }
    for op_str, op_func in sorted(ops.items(), key=lambda x: -len(x[0])):
        if op_str in condition:
            parts = condition.split(op_str, 1)
            field = parts[0].strip()
            value = parts[1].strip().strip('"\'')
            return field, op_func, value
    raise ValueError(f"Cannot parse condition: {condition}")


def cmd_info(args):
    headers, rows = read_csv(args.file)
    print(f"📊 {args.file}")
    print(f"   Rows: {len(rows):,}")
    print(f"   Columns: {len(headers)}")
    print(f"\n   {'Column':<30} {'Type':>8} {'Unique':>8} {'Empty':>6}")
    print(f"   {'─' * 55}")

    for col in headers:
        values = [r.get(col, "") for r in rows]
        non_empty = [v for v in values if v.strip()]
        unique = len(set(non_empty))
        empty = len(values) - len(non_empty)

        # Guess type
        numeric = sum(1 for v in non_empty if re.match(r'^-?\d+\.?\d*$', v))
        col_type = "number" if numeric > len(non_empty) * 0.8 else "text"

        print(f"   {col:<30} {col_type:>8} {unique:>8} {empty:>6}")

    # Show sample
    print(f"\n   First 3 rows:")
    for row in rows[:3]:
        vals = ", ".join(f"{k}={v}" for k, v in list(row.items())[:5])
        print(f"   → {vals}")


def cmd_filter(args):
    headers, rows = read_csv(args.file)
    field, op_func, value = parse_condition(args.condition)

    filtered = []
    for row in rows:
        row_val = row.get(field, "")
        matched = False
        try:
            # Try numeric comparison first
            num_row = float(row_val)
            num_val = float(value)
            matched = op_func(num_row, num_val)
        except (ValueError, TypeError):
            # Fall back to string comparison only if numeric failed
            try:
                matched = op_func(row_val, value)
            except TypeError:
                matched = False
        if matched:
            filtered.append(row)

    out = args.output or f"{Path(args.file).stem}_filtered.csv"
    write_csv(out, headers, filtered)
    print(f"✅ {len(filtered)}/{len(rows)} rows → {out}")


def cmd_select(args):
    headers, rows = read_csv(args.file)
    cols = [c.strip() for c in args.columns.split(",")]
    missing = [c for c in cols if c not in headers]
    if missing:
        print(f"⚠ Unknown columns: {missing}. Available: {headers}")
        sys.exit(1)

    selected = [{c: row.get(c, "") for c in cols} for row in rows]
    out = args.output or f"{Path(args.file).stem}_selected.csv"
    write_csv(out, cols, selected)
    print(f"✅ {len(cols)} columns, {len(selected)} rows → {out}")


def cmd_sort(args):
    headers, rows = read_csv(args.file)

    def sort_key(row):
        val = row.get(args.by, "")
        try:
            return (0, float(val))
        except ValueError:
            return (1, val.lower())

    rows.sort(key=sort_key, reverse=args.desc)
    out = args.output or f"{Path(args.file).stem}_sorted.csv"
    write_csv(out, headers, rows)
    print(f"✅ Sorted by '{args.by}' {'desc' if args.desc else 'asc'} → {out}")


def cmd_dedup(args):
    headers, rows = read_csv(args.file)
    key_col = args.by
    seen = set()
    deduped = []
    for row in rows:
        key = row.get(key_col, "")
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    removed = len(rows) - len(deduped)
    out = args.output or f"{Path(args.file).stem}_deduped.csv"
    write_csv(out, headers, deduped)
    print(f"✅ Removed {removed} duplicates ({len(deduped)} unique) → {out}")


def cmd_merge(args):
    h1, rows1 = read_csv(args.file1)
    h2, rows2 = read_csv(args.file2)
    key = args.on

    lookup = {r[key]: r for r in rows2 if key in r}
    all_headers = list(dict.fromkeys(h1 + [h for h in h2 if h not in h1]))

    merged = []
    for row in rows1:
        k = row.get(key, "")
        if k in lookup:
            combined = {**row, **lookup[k]}
            merged.append(combined)
        elif not args.inner:
            merged.append(row)

    out = args.output or "merged.csv"
    write_csv(out, all_headers, merged)
    print(f"✅ Merged {len(merged)} rows → {out}")


def cmd_convert(args):
    headers, rows = read_csv(args.file)
    out_format = args.to

    if out_format == "json":
        out = args.output or f"{Path(args.file).stem}.json"
        Path(out).write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    elif out_format == "jsonl":
        out = args.output or f"{Path(args.file).stem}.jsonl"
        with open(out, "w") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    elif out_format == "md":
        out = args.output or f"{Path(args.file).stem}.md"
        lines = [f"| {' | '.join(headers)} |", f"| {' | '.join('---' for _ in headers)} |"]
        for row in rows[:100]:
            vals = [row.get(h, "") for h in headers]
            lines.append(f"| {' | '.join(vals)} |")
        if len(rows) > 100:
            lines.append(f"\n*...and {len(rows) - 100} more rows*")
        Path(out).write_text("\n".join(lines))
    else:
        print(f"Unknown format: {out_format}")
        sys.exit(1)

    print(f"✅ Converted {len(rows)} rows → {out}")


def cmd_split(args):
    headers, rows = read_csv(args.file)
    output_dir = Path(args.output or "split")
    output_dir.mkdir(parents=True, exist_ok=True)

    groups = defaultdict(list)
    for row in rows:
        key = row.get(args.by, "unknown").strip() or "empty"
        # Sanitize filename
        safe_key = re.sub(r'[^\w\-]', '_', key)[:50]
        groups[safe_key].append(row)

    for key, group_rows in groups.items():
        out = output_dir / f"{key}.csv"
        write_csv(str(out), headers, group_rows)
        print(f"  {key}: {len(group_rows)} rows → {out.name}")

    print(f"\n✅ Split into {len(groups)} files → {output_dir}/")


def main():
    parser = argparse.ArgumentParser(description="CSV toolkit — no pandas required")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", help="Show CSV info and stats")
    p.add_argument("file")

    p = sub.add_parser("filter", help="Filter rows by condition")
    p.add_argument("file")
    p.add_argument("condition", help='e.g. "age > 30" or "status == active"')
    p.add_argument("--output", "-o")

    p = sub.add_parser("select", help="Select specific columns")
    p.add_argument("file")
    p.add_argument("columns", help="Comma-separated column names")
    p.add_argument("--output", "-o")

    p = sub.add_parser("sort", help="Sort rows")
    p.add_argument("file")
    p.add_argument("--by", required=True, help="Column to sort by")
    p.add_argument("--desc", action="store_true")
    p.add_argument("--output", "-o")

    p = sub.add_parser("dedup", help="Remove duplicates")
    p.add_argument("file")
    p.add_argument("--by", required=True, help="Column for deduplication")
    p.add_argument("--output", "-o")

    p = sub.add_parser("merge", help="Merge two CSV files")
    p.add_argument("file1")
    p.add_argument("file2")
    p.add_argument("--on", required=True, help="Join column")
    p.add_argument("--inner", action="store_true", help="Inner join only")
    p.add_argument("--output", "-o")

    p = sub.add_parser("convert", help="Convert to another format")
    p.add_argument("file")
    p.add_argument("--to", required=True, choices=["json", "jsonl", "md"])
    p.add_argument("--output", "-o")

    p = sub.add_parser("split", help="Split by column value")
    p.add_argument("file")
    p.add_argument("--by", required=True, help="Column to split by")
    p.add_argument("--output", "-o")

    args = parser.parse_args()
    globals()[f"cmd_{args.command}"](args)


if __name__ == "__main__":
    main()
