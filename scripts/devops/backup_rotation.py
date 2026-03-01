#!/usr/bin/env python3
"""
Backup Rotation Manager — Automated backup with configurable retention.

Creates timestamped backups of files/directories and manages retention
using a grandfather-father-son (GFS) rotation scheme.

Usage:
    python backup_rotation.py --source /data/db --dest /backups/db
    python backup_rotation.py --source ./app --dest ./backups --keep-daily 7 --keep-weekly 4
    python backup_rotation.py --source /etc --dest /backups/etc --compress gz
    python backup_rotation.py --list /backups/db                    # List existing backups
    python backup_rotation.py --cleanup /backups/db --keep-daily 7  # Remove old backups

Requirements:
    No external dependencies (stdlib only).
"""

import argparse
import json
import os
import shutil
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path


def create_backup(source: str, dest: str, compress: str = "none") -> dict:
    """Create a timestamped backup."""
    source_path = Path(source)
    dest_path = Path(dest)
    
    if not source_path.exists():
        raise FileNotFoundError(f"Source not found: {source}")
    
    dest_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = source_path.name
    
    if compress != "none":
        ext = {"gz": ".tar.gz", "bz2": ".tar.bz2", "xz": ".tar.xz"}[compress]
        backup_name = f"{name}_{timestamp}{ext}"
        backup_path = dest_path / backup_name
        
        mode = {"gz": "w:gz", "bz2": "w:bz2", "xz": "w:xz"}[compress]
        with tarfile.open(backup_path, mode) as tar:
            tar.add(source_path, arcname=name)
    else:
        backup_name = f"{name}_{timestamp}"
        backup_path = dest_path / backup_name
        
        if source_path.is_dir():
            shutil.copytree(source_path, backup_path)
        else:
            shutil.copy2(source_path, backup_path)
    
    size = sum(f.stat().st_size for f in backup_path.rglob("*")) if backup_path.is_dir() else backup_path.stat().st_size
    
    return {
        "name": backup_name,
        "path": str(backup_path),
        "size_bytes": size,
        "size_human": _human_size(size),
        "timestamp": timestamp,
        "compressed": compress != "none",
    }


def list_backups(dest: str) -> list[dict]:
    """List existing backups sorted by date."""
    dest_path = Path(dest)
    if not dest_path.exists():
        return []
    
    backups = []
    for item in sorted(dest_path.iterdir()):
        if item.name.startswith("."):
            continue
        
        # Try to extract timestamp from name
        import re
        match = re.search(r'(\d{8}_\d{6})', item.name)
        timestamp = match.group(1) if match else ""
        
        size = sum(f.stat().st_size for f in item.rglob("*")) if item.is_dir() else item.stat().st_size
        
        backups.append({
            "name": item.name,
            "path": str(item),
            "timestamp": timestamp,
            "size_bytes": size,
            "size_human": _human_size(size),
            "type": "directory" if item.is_dir() else "archive",
            "created": datetime.fromtimestamp(item.stat().st_ctime).isoformat(),
        })
    
    return sorted(backups, key=lambda b: b["timestamp"], reverse=True)


def cleanup_backups(dest: str, keep_daily: int = 7, keep_weekly: int = 4,
                    keep_monthly: int = 6, dry_run: bool = False) -> dict:
    """Apply GFS retention policy."""
    backups = list_backups(dest)
    
    if not backups:
        return {"kept": 0, "removed": 0, "removed_items": []}
    
    now = datetime.now()
    keep = set()
    remove = []
    
    for backup in backups:
        if not backup["timestamp"]:
            keep.add(backup["name"])  # Keep unrecognized items
            continue
        
        try:
            ts = datetime.strptime(backup["timestamp"], "%Y%m%d_%H%M%S")
        except ValueError:
            keep.add(backup["name"])
            continue
        
        age = (now - ts).days
        
        # Daily: keep last N days
        if age < keep_daily:
            keep.add(backup["name"])
        # Weekly: keep Sunday backups for N weeks
        elif age < keep_weekly * 7 and ts.weekday() == 6:
            keep.add(backup["name"])
        # Monthly: keep 1st of month for N months
        elif age < keep_monthly * 30 and ts.day == 1:
            keep.add(backup["name"])
    
    # Always keep the latest backup
    if backups:
        keep.add(backups[0]["name"])
    
    for backup in backups:
        if backup["name"] not in keep:
            remove.append(backup)
            if not dry_run:
                path = Path(backup["path"])
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
    
    return {
        "kept": len(keep),
        "removed": len(remove),
        "dry_run": dry_run,
        "removed_items": [r["name"] for r in remove],
        "freed_bytes": sum(r["size_bytes"] for r in remove),
        "freed_human": _human_size(sum(r["size_bytes"] for r in remove)),
    }


def _human_size(size: int) -> str:
    """Convert bytes to human-readable size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def main():
    parser = argparse.ArgumentParser(description="Backup rotation manager")
    parser.add_argument("--source", help="Source file/directory to backup")
    parser.add_argument("--dest", help="Backup destination directory")
    parser.add_argument("--compress", choices=["none", "gz", "bz2", "xz"], default="none")
    parser.add_argument("--list", metavar="DIR", help="List backups in directory")
    parser.add_argument("--cleanup", metavar="DIR", help="Apply retention policy to directory")
    parser.add_argument("--keep-daily", type=int, default=7, help="Keep daily backups for N days")
    parser.add_argument("--keep-weekly", type=int, default=4, help="Keep weekly backups for N weeks")
    parser.add_argument("--keep-monthly", type=int, default=6, help="Keep monthly backups for N months")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    
    if args.list:
        backups = list_backups(args.list)
        if args.format == "json":
            print(json.dumps(backups, indent=2))
        else:
            print(f"📦 Backups in {args.list} ({len(backups)} found)\n")
            for b in backups:
                print(f"  {b['name']:40s}  {b['size_human']:>10s}  {b['timestamp']}")
    
    elif args.cleanup:
        result = cleanup_backups(args.cleanup, args.keep_daily, args.keep_weekly,
                                args.keep_monthly, args.dry_run)
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            prefix = "[DRY RUN] " if result["dry_run"] else ""
            print(f"{prefix}🧹 Cleanup: kept {result['kept']}, removed {result['removed']}")
            print(f"{prefix}Freed: {result['freed_human']}")
            if result["removed_items"]:
                print(f"\n{prefix}Removed:")
                for name in result["removed_items"]:
                    print(f"  ❌ {name}")
    
    elif args.source and args.dest:
        result = create_backup(args.source, args.dest, args.compress)
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(f"✅ Backup created: {result['name']}")
            print(f"   Size: {result['size_human']}")
            print(f"   Path: {result['path']}")
    
    else:
        parser.error("Use --source/--dest to backup, --list to view, or --cleanup to rotate")


if __name__ == "__main__":
    main()
