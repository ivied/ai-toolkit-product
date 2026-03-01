#!/usr/bin/env python3
"""
JSON Transformer — Filter, flatten, reshape, and convert JSON data.

Swiss-army knife for JSON manipulation from the command line.

Usage:
    python json_transformer.py flatten input.json
    python json_transformer.py pick input.json --fields name,email,age
    python json_transformer.py filter input.json --where "age>30"
    python json_transformer.py convert input.json --to csv
    python json_transformer.py merge file1.json file2.json
    cat data.json | python json_transformer.py stats --stdin

No external dependencies required.
"""

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter


def load_json(path=None, from_stdin=False):
    if from_stdin or (path is None and not sys.stdin.isatty()):
        return json.load(sys.stdin)
    with open(path) as f:
        return json.load(f)


def flatten_dict(d, parent_key="", sep="."):
    """Flatten nested dict."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.extend(flatten_dict(item, f"{new_key}[{i}]", sep).items())
                else:
                    items.append((f"{new_key}[{i}]", item))
        else:
            items.append((new_key, v))
    return dict(items)


def cmd_flatten(data):
    if isinstance(data, list):
        return [flatten_dict(item) if isinstance(item, dict) else item for item in data]
    elif isinstance(data, dict):
        return flatten_dict(data)
    return data


def cmd_pick(data, fields):
    """Pick specific fields from objects."""
    field_list = [f.strip() for f in fields.split(",")]
    
    def pick_from(obj):
        if not isinstance(obj, dict):
            return obj
        result = {}
        for field in field_list:
            parts = field.split(".")
            val = obj
            for part in parts:
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            result[field] = val
        return result
    
    if isinstance(data, list):
        return [pick_from(item) for item in data]
    return pick_from(data)


def cmd_filter(data, where):
    """Filter array items by condition."""
    if not isinstance(data, list):
        print("Error: filter requires an array", file=sys.stderr)
        return data
    
    # Parse simple conditions: field>value, field==value, field!=value, field<value
    match = re.match(r'(\w[\w.]*)\s*(==|!=|>=|<=|>|<|contains|startswith)\s*(.+)', where)
    if not match:
        print(f"Invalid filter: {where}", file=sys.stderr)
        return data
    
    field, op, value = match.group(1), match.group(2), match.group(3).strip().strip("\"'")
    
    def get_nested(obj, path):
        for part in path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
        return obj
    
    def matches(item):
        val = get_nested(item, field)
        if val is None:
            return False
        # Try numeric comparison
        try:
            val_num = float(val)
            cmp_num = float(value)
            ops = {"==": val_num == cmp_num, "!=": val_num != cmp_num,
                   ">": val_num > cmp_num, "<": val_num < cmp_num,
                   ">=": val_num >= cmp_num, "<=": val_num <= cmp_num}
            if op in ops:
                return ops[op]
        except (ValueError, TypeError):
            pass
        # String comparison
        val_str = str(val)
        ops = {"==": val_str == value, "!=": val_str != value,
               "contains": value in val_str, "startswith": val_str.startswith(value),
               ">": val_str > value, "<": val_str < value}
        return ops.get(op, False)
    
    return [item for item in data if matches(item)]


def cmd_convert(data, to_format):
    """Convert JSON to other formats."""
    if to_format == "csv":
        if not isinstance(data, list) or not data:
            return "[]"
        flat = [flatten_dict(item) if isinstance(item, dict) else {"value": item} for item in data]
        keys = list(dict.fromkeys(k for item in flat for k in item.keys()))
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=keys)
        writer.writeheader()
        for item in flat:
            writer.writerow({k: item.get(k, "") for k in keys})
        return output.getvalue()
    
    elif to_format == "yaml":
        def to_yaml(obj, indent=0):
            lines = []
            prefix = "  " * indent
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}:")
                        lines.append(to_yaml(v, indent + 1))
                    else:
                        lines.append(f"{prefix}{k}: {json.dumps(v)}")
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        lines.append(f"{prefix}-")
                        lines.append(to_yaml(item, indent + 1))
                    else:
                        lines.append(f"{prefix}- {json.dumps(item)}")
            else:
                lines.append(f"{prefix}{json.dumps(obj)}")
            return "\n".join(lines)
        return to_yaml(data)
    
    elif to_format == "table":
        if not isinstance(data, list) or not data:
            return str(data)
        flat = [flatten_dict(item) if isinstance(item, dict) else {"value": item} for item in data]
        keys = list(dict.fromkeys(k for item in flat for k in item.keys()))
        
        widths = {k: max(len(k), max((len(str(item.get(k, "")))[:30] for item in flat), default=0)) for k in keys}
        
        header = " | ".join(k.ljust(widths[k])[:30] for k in keys)
        separator = "-+-".join("-" * min(widths[k], 30) for k in keys)
        rows = []
        for item in flat[:50]:
            row = " | ".join(str(item.get(k, "")).ljust(widths[k])[:30] for k in keys)
            rows.append(row)
        
        return f"{header}\n{separator}\n" + "\n".join(rows)
    
    return json.dumps(data, indent=2)


def cmd_stats(data):
    """Show statistics about JSON data."""
    stats = {"type": type(data).__name__}
    
    if isinstance(data, list):
        stats["count"] = len(data)
        types = Counter(type(item).__name__ for item in data)
        stats["item_types"] = dict(types)
        if data and isinstance(data[0], dict):
            all_keys = Counter()
            for item in data:
                for k in item.keys():
                    all_keys[k] += 1
            stats["fields"] = {k: {"count": c, "coverage": f"{c/len(data)*100:.0f}%"}
                              for k, c in all_keys.most_common()}
    elif isinstance(data, dict):
        stats["keys"] = len(data)
        stats["key_list"] = list(data.keys())
        stats["nested_depth"] = _depth(data)
    
    return json.dumps(stats, indent=2)


def _depth(obj, current=0):
    if isinstance(obj, dict):
        return max((_depth(v, current + 1) for v in obj.values()), default=current)
    elif isinstance(obj, list):
        return max((_depth(v, current + 1) for v in obj), default=current)
    return current


def cmd_merge(files):
    """Merge multiple JSON files."""
    result = []
    for f in files:
        data = load_json(f)
        if isinstance(data, list):
            result.extend(data)
        else:
            result.append(data)
    return result


def main():
    parser = argparse.ArgumentParser(description="JSON transformer toolkit")
    sub = parser.add_subparsers(dest="command")
    
    for cmd in ["flatten", "stats"]:
        p = sub.add_parser(cmd)
        p.add_argument("file", nargs="?")
        p.add_argument("--stdin", action="store_true")
    
    p = sub.add_parser("pick")
    p.add_argument("file", nargs="?"); p.add_argument("--fields", required=True)
    p.add_argument("--stdin", action="store_true")
    
    p = sub.add_parser("filter")
    p.add_argument("file", nargs="?"); p.add_argument("--where", required=True)
    p.add_argument("--stdin", action="store_true")
    
    p = sub.add_parser("convert")
    p.add_argument("file", nargs="?"); p.add_argument("--to", required=True, choices=["csv", "yaml", "table"])
    p.add_argument("--stdin", action="store_true")
    
    p = sub.add_parser("merge")
    p.add_argument("files", nargs="+")
    
    args = parser.parse_args()
    
    if args.command == "merge":
        print(json.dumps(cmd_merge(args.files), indent=2))
    elif args.command:
        stdin = getattr(args, "stdin", False)
        data = load_json(getattr(args, "file", None), stdin)
        
        if args.command == "flatten":
            print(json.dumps(cmd_flatten(data), indent=2))
        elif args.command == "pick":
            print(json.dumps(cmd_pick(data, args.fields), indent=2))
        elif args.command == "filter":
            print(json.dumps(cmd_filter(data, args.where), indent=2))
        elif args.command == "convert":
            print(cmd_convert(data, args.to))
        elif args.command == "stats":
            print(cmd_stats(data))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
