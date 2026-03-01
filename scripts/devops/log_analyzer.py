#!/usr/bin/env python3
"""
Log Analyzer — Parse, filter, and summarize log files.

Analyzes log files to extract error patterns, frequency distributions,
and generates human-readable reports.

Usage:
    python log_analyzer.py app.log
    python log_analyzer.py --pattern "ERROR|WARN" /var/log/app.log
    python log_analyzer.py --top 20 --format json access.log
    python log_analyzer.py --since "2024-01-01" --until "2024-01-31" app.log

Requirements:
    No external dependencies (stdlib only).
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


# Common log patterns
PATTERNS = {
    "timestamp": r'(\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2})',
    "ip": r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
    "level": r'\b(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\b',
    "http_status": r'\b([1-5]\d{2})\b',
    "url_path": r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]*)',
    "email": r'[\w.+-]+@[\w-]+\.[\w.]+',
}


def parse_log_line(line: str) -> dict:
    """Extract structured data from a log line."""
    result = {"raw": line.rstrip()}
    
    for name, pattern in PATTERNS.items():
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            result[name] = match.group(1) if match.lastindex else match.group(0)
    
    return result


def analyze_logs(lines: list[str], pattern: str | None = None,
                 since: str | None = None, until: str | None = None) -> dict:
    """Analyze log lines and produce statistics."""
    
    level_counts = Counter()
    status_counts = Counter()
    ip_counts = Counter()
    error_messages = Counter()
    hourly = Counter()
    url_counts = Counter()
    total = 0
    filtered = 0
    
    for line in lines:
        if not line.strip():
            continue
        total += 1
        
        # Pattern filter
        if pattern and not re.search(pattern, line, re.IGNORECASE):
            continue
        
        parsed = parse_log_line(line)
        
        # Time filter
        if (since or until) and "timestamp" in parsed:
            try:
                ts = datetime.fromisoformat(parsed["timestamp"].replace("/", "-"))
                if since and ts < datetime.fromisoformat(since):
                    continue
                if until and ts > datetime.fromisoformat(until):
                    continue
            except (ValueError, TypeError):
                pass
        
        filtered += 1
        
        if "level" in parsed:
            level_counts[parsed["level"].upper()] += 1
        
        if "http_status" in parsed:
            status_counts[parsed["http_status"]] += 1
        
        if "ip" in parsed:
            ip_counts[parsed["ip"]] += 1
        
        if "url_path" in parsed:
            url_counts[parsed["url_path"]] += 1
        
        if "timestamp" in parsed:
            try:
                hour = parsed["timestamp"][11:13]
                hourly[hour] += 1
            except (IndexError, TypeError):
                pass
        
        # Track error messages
        level = parsed.get("level", "").upper()
        if level in ("ERROR", "FATAL", "CRITICAL", "WARN", "WARNING"):
            # Extract message after level
            match = re.search(r'(?:ERROR|FATAL|CRITICAL|WARN(?:ING)?)\s*[:\]]\s*(.+)', line)
            if match:
                msg = match.group(1)[:100]
                error_messages[msg] += 1
    
    return {
        "total_lines": total,
        "filtered_lines": filtered,
        "levels": dict(level_counts.most_common()),
        "http_statuses": dict(status_counts.most_common()),
        "top_ips": dict(ip_counts.most_common(20)),
        "top_urls": dict(url_counts.most_common(20)),
        "top_errors": dict(error_messages.most_common(20)),
        "hourly_distribution": dict(sorted(hourly.items())),
        "error_rate": (
            (level_counts.get("ERROR", 0) + level_counts.get("FATAL", 0) + level_counts.get("CRITICAL", 0))
            / max(filtered, 1) * 100
        ),
    }


def format_report(stats: dict) -> str:
    """Format analysis as human-readable report."""
    lines = ["# Log Analysis Report\n"]
    lines.append(f"**Total lines:** {stats['total_lines']:,}")
    lines.append(f"**Filtered lines:** {stats['filtered_lines']:,}")
    lines.append(f"**Error rate:** {stats['error_rate']:.1f}%\n")
    
    if stats["levels"]:
        lines.append("## Log Levels")
        for level, count in stats["levels"].items():
            bar = "█" * min(50, int(count / max(stats["levels"].values()) * 50))
            lines.append(f"  {level:10s} {count:>8,}  {bar}")
        lines.append("")
    
    if stats["top_errors"]:
        lines.append("## Top Errors")
        for msg, count in list(stats["top_errors"].items())[:10]:
            lines.append(f"  [{count:>5}x] {msg}")
        lines.append("")
    
    if stats["http_statuses"]:
        lines.append("## HTTP Status Codes")
        for status, count in stats["http_statuses"].items():
            emoji = "✅" if status.startswith("2") else "⚠️" if status.startswith("4") else "❌" if status.startswith("5") else "ℹ️"
            lines.append(f"  {emoji} {status}: {count:,}")
        lines.append("")
    
    if stats["top_ips"]:
        lines.append("## Top IP Addresses")
        for ip, count in list(stats["top_ips"].items())[:10]:
            lines.append(f"  {ip:20s} {count:>8,} requests")
        lines.append("")
    
    if stats["hourly_distribution"]:
        lines.append("## Hourly Distribution")
        max_val = max(stats["hourly_distribution"].values()) if stats["hourly_distribution"] else 1
        for hour, count in sorted(stats["hourly_distribution"].items()):
            bar = "▓" * int(count / max_val * 40)
            lines.append(f"  {hour}:00  {bar} {count}")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze log files")
    parser.add_argument("logfile", nargs="?", help="Log file path (or stdin)")
    parser.add_argument("--pattern", help="Regex pattern to filter lines")
    parser.add_argument("--since", help="Start date (ISO format)")
    parser.add_argument("--until", help="End date (ISO format)")
    parser.add_argument("--top", type=int, default=20, help="Top N results")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    
    if args.logfile:
        with open(args.logfile) as f:
            lines = f.readlines()
    elif not sys.stdin.isatty():
        lines = sys.stdin.readlines()
    else:
        parser.error("Provide a log file or pipe via stdin")
    
    stats = analyze_logs(lines, args.pattern, args.since, args.until)
    
    if args.format == "json":
        print(json.dumps(stats, indent=2))
    else:
        print(format_report(stats))


if __name__ == "__main__":
    main()
