#!/usr/bin/env python3
"""
SQLite Query Tool — Run SQL queries on CSV/JSON data using SQLite.

Load CSV or JSON files as tables and query them with standard SQL.
No database setup needed — creates an in-memory SQLite database.

Usage:
    python sqlite_query.py --csv users.csv --query "SELECT * FROM data WHERE age > 30"
    python sqlite_query.py --json orders.json --query "SELECT status, COUNT(*) FROM data GROUP BY status"
    python sqlite_query.py --csv sales.csv --interactive

No external dependencies (uses Python stdlib sqlite3).
"""

import argparse
import csv
import json
import readline  # For interactive history
import sqlite3
import sys
from pathlib import Path


def load_csv_to_db(conn, filepath, table_name="data"):
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows: return 0
    
    cols = list(rows[0].keys())
    # Detect types
    col_types = {}
    for col in cols:
        sample = [r[col] for r in rows[:100] if r.get(col)]
        try:
            [float(v) for v in sample if v]
            col_types[col] = "REAL" if any("." in v for v in sample if v) else "INTEGER"
        except ValueError:
            col_types[col] = "TEXT"
    
    create_sql = f"CREATE TABLE {table_name} ({', '.join(f'{c} {col_types[c]}' for c in cols)})"
    conn.execute(create_sql)
    
    placeholders = ", ".join("?" * len(cols))
    for row in rows:
        values = []
        for c in cols:
            v = row.get(c, "")
            if col_types[c] in ("INTEGER", "REAL") and v:
                try: v = float(v) if col_types[c] == "REAL" else int(v)
                except ValueError: pass
            values.append(v if v else None)
        conn.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
    
    conn.commit()
    return len(rows)


def load_json_to_db(conn, filepath, table_name="data"):
    with open(filepath) as f:
        data = json.load(f)
    if not isinstance(data, list) or not data: return 0
    
    # Flatten nested objects
    flat_rows = []
    for item in data:
        if isinstance(item, dict):
            flat = {}
            for k, v in item.items():
                if isinstance(v, (dict, list)):
                    flat[k] = json.dumps(v)
                else:
                    flat[k] = v
            flat_rows.append(flat)
    
    if not flat_rows: return 0
    cols = list(dict.fromkeys(k for row in flat_rows for k in row.keys()))
    
    col_defs = ", ".join(f'"{c}" TEXT' for c in cols)
    conn.execute(f"CREATE TABLE {table_name} ({col_defs})")
    
    placeholders = ", ".join("?" * len(cols))
    for row in flat_rows:
        values = [str(row.get(c, "")) if row.get(c) is not None else None for c in cols]
        conn.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
    
    conn.commit()
    return len(flat_rows)


def run_query(conn, sql, output_format="table"):
    cursor = conn.execute(sql)
    cols = [d[0] for d in cursor.description] if cursor.description else []
    rows = cursor.fetchall()
    
    if output_format == "json":
        return json.dumps([dict(zip(cols, row)) for row in rows], indent=2, default=str)
    elif output_format == "csv":
        import io
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(cols)
        writer.writerows(rows)
        return out.getvalue()
    else:
        if not rows: return "(no results)"
        widths = {c: max(len(c), max((len(str(row[i])[:40]) for row in rows), default=0)) for i, c in enumerate(cols)}
        header = " | ".join(c.ljust(widths[c])[:40] for c in cols)
        sep = "-+-".join("-" * min(widths[c], 40) for c in cols)
        data_rows = [" | ".join(str(row[i]).ljust(widths[cols[i]])[:40] for i in range(len(cols))) for row in rows[:100]]
        result = f"{header}\n{sep}\n" + "\n".join(data_rows)
        if len(rows) > 100: result += f"\n... ({len(rows)} total rows)"
        return result


def interactive(conn):
    print("SQLite interactive mode. Type SQL queries. Ctrl+D to exit.\n")
    print("Tables: ", end="")
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(", ".join(t[0] for t in tables))
    print()
    
    while True:
        try:
            sql = input("sql> ").strip()
            if not sql: continue
            if sql.lower() in ("quit", "exit", ".quit"): break
            if sql.lower() == ".tables":
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                print(", ".join(t[0] for t in tables))
                continue
            if sql.lower().startswith(".schema"):
                for t in conn.execute("SELECT sql FROM sqlite_master WHERE type='table'").fetchall():
                    print(t[0])
                continue
            
            print(run_query(conn, sql))
            print()
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Query CSV/JSON with SQL")
    parser.add_argument("--csv", help="CSV file to load")
    parser.add_argument("--json", dest="json_file", help="JSON file to load")
    parser.add_argument("--query", "-q", help="SQL query to run")
    parser.add_argument("--interactive", "-i", action="store_true")
    parser.add_argument("--table", default="data", help="Table name (default: data)")
    parser.add_argument("--output", choices=["table", "json", "csv"], default="table")
    args = parser.parse_args()
    
    conn = sqlite3.connect(":memory:")
    
    count = 0
    if args.csv:
        count = load_csv_to_db(conn, args.csv, args.table)
        print(f"📊 Loaded {count} rows from {args.csv}", file=sys.stderr)
    elif args.json_file:
        count = load_json_to_db(conn, args.json_file, args.table)
        print(f"📊 Loaded {count} rows from {args.json_file}", file=sys.stderr)
    
    if args.interactive:
        interactive(conn)
    elif args.query:
        print(run_query(conn, args.query, args.output))
    else:
        parser.error("Provide --query or --interactive")
    
    conn.close()


if __name__ == "__main__":
    main()
