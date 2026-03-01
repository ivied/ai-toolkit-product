#!/usr/bin/env python3
"""
Report Generator — Create formatted reports from data files.

Takes CSV/JSON data and generates HTML or Markdown reports with
charts (ASCII), tables, and summary statistics.

Usage:
    python report_generator.py input.csv --title "Sales Report"
    python report_generator.py data.json --format html --output report.html
    python report_generator.py input.csv --group-by category --sum amount

No external dependencies required.
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def load_data(path: str) -> list[dict]:
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    elif ext == ".json":
        with open(path) as f:
            data = json.load(f)
            return data if isinstance(data, list) else [data]
    else:
        raise ValueError(f"Unsupported format: {ext}")


def compute_stats(values: list) -> dict:
    nums = []
    for v in values:
        try: nums.append(float(v))
        except (ValueError, TypeError): pass
    
    if not nums:
        return {"count": len(values), "unique": len(set(str(v) for v in values))}
    
    return {
        "count": len(nums), "sum": sum(nums),
        "min": min(nums), "max": max(nums),
        "avg": sum(nums) / len(nums),
        "median": sorted(nums)[len(nums) // 2],
    }


def group_and_aggregate(data: list[dict], group_by: str, agg_field: str = None, agg_func: str = "sum") -> list[dict]:
    groups = defaultdict(list)
    for row in data:
        key = row.get(group_by, "N/A")
        groups[key].append(row)
    
    result = []
    for key, rows in sorted(groups.items()):
        entry = {"group": key, "count": len(rows)}
        if agg_field:
            values = [float(r.get(agg_field, 0)) for r in rows if r.get(agg_field)]
            if values:
                entry["sum"] = sum(values)
                entry["avg"] = sum(values) / len(values)
                entry["min"] = min(values)
                entry["max"] = max(values)
        result.append(entry)
    return result


def ascii_bar_chart(data: list[dict], label_key: str, value_key: str, width: int = 40) -> str:
    if not data: return ""
    max_val = max(d.get(value_key, 0) for d in data) or 1
    max_label = max(len(str(d.get(label_key, ""))) for d in data)
    
    lines = []
    for d in data:
        label = str(d.get(label_key, ""))
        val = d.get(value_key, 0)
        bar_len = int(val / max_val * width)
        bar = "█" * bar_len + "░" * (width - bar_len)
        lines.append(f"  {label:<{max_label}} |{bar}| {val:,.1f}" if isinstance(val, float)
                     else f"  {label:<{max_label}} |{bar}| {val:,}")
    return "\n".join(lines)


def generate_markdown(data: list[dict], title: str, group_by: str = None, 
                      agg_field: str = None) -> str:
    lines = [f"# {title}", f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"]
    
    # Summary stats
    lines.append("## Summary\n")
    lines.append(f"- **Total records:** {len(data):,}")
    lines.append(f"- **Fields:** {', '.join(data[0].keys()) if data else 'none'}\n")
    
    # Per-field stats
    if data:
        lines.append("## Field Statistics\n")
        for field in data[0].keys():
            values = [row.get(field) for row in data]
            stats = compute_stats(values)
            lines.append(f"### {field}")
            for k, v in stats.items():
                lines.append(f"- {k}: {v:,.2f}" if isinstance(v, float) else f"- {k}: {v}")
            lines.append("")
    
    # Grouping
    if group_by:
        grouped = group_and_aggregate(data, group_by, agg_field)
        lines.append(f"## By {group_by}\n")
        
        chart = ascii_bar_chart(grouped, "group", agg_field and "sum" or "count")
        if chart:
            lines.append("```")
            lines.append(chart)
            lines.append("```\n")
        
        for g in grouped:
            extra = f" | Sum: {g['sum']:,.2f}" if "sum" in g else ""
            lines.append(f"- **{g['group']}**: {g['count']} records{extra}")
        lines.append("")
    
    # Data table (first 20 rows)
    if data:
        lines.append("## Data Preview (first 20 rows)\n")
        keys = list(data[0].keys())
        lines.append("| " + " | ".join(keys) + " |")
        lines.append("| " + " | ".join("---" for _ in keys) + " |")
        for row in data[:20]:
            vals = [str(row.get(k, ""))[:30] for k in keys]
            lines.append("| " + " | ".join(vals) + " |")
    
    return "\n".join(lines)


def generate_html(data: list[dict], title: str, group_by: str = None,
                   agg_field: str = None) -> str:
    md = generate_markdown(data, title, group_by, agg_field)
    # Simple MD→HTML conversion
    html = ["<!DOCTYPE html><html><head>", f"<title>{title}</title>",
            "<style>body{font-family:system-ui;max-width:900px;margin:40px auto;padding:0 20px;color:#333}",
            "table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px;text-align:left}",
            "th{background:#f5f5f5}pre{background:#f8f8f8;padding:15px;overflow-x:auto}",
            "h1{color:#2c3e50}h2{color:#34495e;border-bottom:1px solid #eee;padding-bottom:5px}</style>",
            "</head><body>"]
    
    for line in md.split("\n"):
        if line.startswith("# "): html.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "): html.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "): html.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "): html.append(f"<li>{line[2:]}</li>")
        elif line.startswith("| "): html.append(f"<tr>{''.join(f'<td>{c.strip()}</td>' for c in line.strip('|').split('|'))}</tr>")
        elif line.startswith("```"): html.append("<pre>" if "```" not in html[-1:] else "</pre>")
        elif line.startswith("*"): html.append(f"<em>{line.strip('*')}</em>")
        elif line: html.append(f"<p>{line}</p>")
    
    html.append("</body></html>")
    return "\n".join(html)


def main():
    parser = argparse.ArgumentParser(description="Generate reports from data")
    parser.add_argument("input", help="CSV or JSON file")
    parser.add_argument("--title", default="Data Report")
    parser.add_argument("--format", choices=["markdown", "html"], default="markdown")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--group-by", help="Group by field")
    parser.add_argument("--sum", dest="agg_field", help="Field to aggregate")
    args = parser.parse_args()
    
    data = load_data(args.input)
    
    if args.format == "html":
        result = generate_html(data, args.title, args.group_by, args.agg_field)
    else:
        result = generate_markdown(data, args.title, args.group_by, args.agg_field)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"✅ Report saved: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
