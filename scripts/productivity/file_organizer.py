#!/usr/bin/env python3
"""
Smart File Organizer
====================
Organize files in a directory by type, date, or AI-classified category.
Supports dry-run mode, undo, and custom rules.

Usage:
    python file_organizer.py ~/Downloads --mode type
    python file_organizer.py ~/Desktop --mode date --format "%Y/%m"
    python file_organizer.py ./messy/ --mode type --dry-run
    python file_organizer.py ./messy/ --undo  # Restore from log

Modes:
    type  — Organize by file extension (Images/, Documents/, Videos/, etc.)
    date  — Organize by modification date (2024/01/, 2024/02/, etc.)
"""

import argparse
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

TYPE_CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".heic", ".heif", ".avif"},
    "Documents": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp", ".rtf", ".epub"},
    "Text": {".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".log"},
    "Code": {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".rb", ".php", ".swift", ".kt", ".sh", ".bash", ".zsh", ".sql", ".html", ".css"},
    "Archives": {".zip", ".tar", ".gz", ".bz2", ".rar", ".7z", ".xz", ".tgz", ".dmg", ".iso"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2", ".eot"},
    "Data": {".db", ".sqlite", ".sqlite3", ".parquet", ".arrow", ".feather"},
    "Executables": {".exe", ".msi", ".app", ".deb", ".rpm", ".pkg", ".apk", ".ipa"},
}

# Invert for lookup
EXT_TO_CATEGORY = {}
for cat, exts in TYPE_CATEGORIES.items():
    for ext in exts:
        EXT_TO_CATEGORY[ext] = cat


def categorize_by_type(filepath: Path) -> str:
    return EXT_TO_CATEGORY.get(filepath.suffix.lower(), "Other")


def categorize_by_date(filepath: Path, fmt: str) -> str:
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    return mtime.strftime(fmt)


def organize(directory: Path, mode: str, date_format: str, dry_run: bool) -> list[dict]:
    """Organize files and return move log."""
    moves = []
    files = [f for f in directory.iterdir() if f.is_file() and f.name != ".organize_log.json"]

    for f in sorted(files):
        if mode == "type":
            category = categorize_by_type(f)
        elif mode == "date":
            category = categorize_by_date(f, date_format)
        else:
            category = "Other"

        dest_dir = directory / category
        dest = dest_dir / f.name

        # Handle conflicts
        if dest.exists():
            stem, suffix = f.stem, f.suffix
            counter = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        move = {"from": str(f), "to": str(dest), "category": category}
        moves.append(move)

        if dry_run:
            print(f"  [DRY] {f.name} → {category}/")
        else:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
            print(f"  ✓ {f.name} → {category}/")

    return moves


def undo(directory: Path):
    """Undo organization using the log file."""
    log_file = directory / ".organize_log.json"
    if not log_file.exists():
        print("No .organize_log.json found — nothing to undo.")
        return

    moves = json.loads(log_file.read_text())
    restored = 0
    for move in reversed(moves):
        src = Path(move["to"])
        dst = Path(move["from"])
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            restored += 1

    # Clean up empty directories
    for d in sorted(directory.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    log_file.unlink()
    print(f"✅ Restored {restored} files")


def main():
    parser = argparse.ArgumentParser(description="Organize files by type or date")
    parser.add_argument("directory", help="Directory to organize")
    parser.add_argument("--mode", choices=["type", "date"], default="type")
    parser.add_argument("--format", dest="date_format", default="%Y/%m", help="Date format for date mode")
    parser.add_argument("--dry-run", action="store_true", help="Preview without moving")
    parser.add_argument("--undo", action="store_true", help="Undo last organization")
    args = parser.parse_args()

    directory = Path(args.directory).resolve()
    if not directory.is_dir():
        print(f"Error: {directory} is not a directory")
        sys.exit(1)

    if args.undo:
        undo(directory)
        return

    files = [f for f in directory.iterdir() if f.is_file()]
    print(f"📂 {len(files)} files in {directory}")

    if not files:
        print("Nothing to organize.")
        return

    # Show summary
    categories = defaultdict(int)
    for f in files:
        cat = categorize_by_type(f) if args.mode == "type" else categorize_by_date(f, args.date_format)
        categories[cat] += 1

    print(f"\n{'Category':<20} {'Count':>5}")
    print("─" * 26)
    for cat, count in sorted(categories.items()):
        print(f"  {cat:<18} {count:>5}")

    if args.dry_run:
        print("\n[DRY RUN — no files moved]\n")

    moves = organize(directory, args.mode, args.date_format, args.dry_run)

    if not args.dry_run and moves:
        log_file = directory / ".organize_log.json"
        log_file.write_text(json.dumps(moves, indent=2))
        print(f"\n✅ Organized {len(moves)} files. Undo with: python {sys.argv[0]} {directory} --undo")


if __name__ == "__main__":
    main()
