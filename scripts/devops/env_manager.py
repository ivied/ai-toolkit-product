#!/usr/bin/env python3
"""
Environment Variable Manager — Manage .env files across projects.

Compare, merge, validate, and generate .env files. Detect missing
variables, find secrets accidentally committed, and sync environments.

Usage:
    python env_manager.py compare .env .env.production    # Diff two env files
    python env_manager.py validate .env --template .env.example
    python env_manager.py generate .env.example --from-code src/
    python env_manager.py merge .env.local .env.defaults --output .env
    python env_manager.py audit .                         # Find leaked secrets

No external dependencies required.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def parse_env(filepath):
    """Parse a .env file into dict."""
    env = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                env[key] = value
    return env


def cmd_compare(file1, file2):
    """Compare two env files."""
    env1 = parse_env(file1)
    env2 = parse_env(file2)
    
    only1 = set(env1) - set(env2)
    only2 = set(env2) - set(env1)
    common = set(env1) & set(env2)
    different = {k for k in common if env1[k] != env2[k]}
    same = common - different
    
    print(f"📊 Comparing {file1} vs {file2}\n")
    if only1:
        print(f"Only in {file1} ({len(only1)}):")
        for k in sorted(only1): print(f"  + {k}={env1[k][:20]}...")
    if only2:
        print(f"\nOnly in {file2} ({len(only2)}):")
        for k in sorted(only2): print(f"  + {k}={env2[k][:20]}...")
    if different:
        print(f"\nDifferent values ({len(different)}):")
        for k in sorted(different):
            print(f"  ~ {k}: {env1[k][:20]}... → {env2[k][:20]}...")
    print(f"\nSame: {len(same)} | Different: {len(different)} | Only left: {len(only1)} | Only right: {len(only2)}")


def cmd_validate(env_file, template):
    """Validate env file against template."""
    env = parse_env(env_file)
    tmpl = parse_env(template)
    
    missing = set(tmpl) - set(env)
    extra = set(env) - set(tmpl)
    empty = {k for k in env if k in tmpl and not env[k]}
    
    ok = not missing and not empty
    
    print(f"{'✅' if ok else '❌'} Validation: {env_file} against {template}\n")
    if missing:
        print(f"Missing ({len(missing)}):")
        for k in sorted(missing): print(f"  ❌ {k} (default: {tmpl[k][:20]})")
    if empty:
        print(f"\nEmpty ({len(empty)}):")
        for k in sorted(empty): print(f"  ⚠️  {k}")
    if extra:
        print(f"\nExtra ({len(extra)}):")
        for k in sorted(extra): print(f"  ℹ️  {k}")
    
    return 0 if ok else 1


def cmd_generate(output, from_code):
    """Generate .env.example from code by finding env var references."""
    patterns = [
        r'os\.(?:getenv|environ\.get)\(["\'](\w+)["\']',
        r'process\.env\.(\w+)',
        r'\$\{(\w+)\}',
        r'env\(["\'](\w+)["\']',
    ]
    
    found = set()
    for root, dirs, files in os.walk(from_code):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", "__pycache__", ".venv"}]
        for fname in files:
            if not fname.endswith((".py", ".js", ".ts", ".go", ".rs", ".rb", ".yaml", ".yml", ".toml")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath) as f:
                    content = f.read()
                for pattern in patterns:
                    found.update(re.findall(pattern, content))
            except (UnicodeDecodeError, PermissionError):
                continue
    
    with open(output, "w") as f:
        f.write("# Generated .env.example\n# Fill in your values\n\n")
        for var in sorted(found):
            f.write(f"{var}=\n")
    
    print(f"✅ Generated {output} with {len(found)} variables")
    for v in sorted(found): print(f"  • {v}")


def cmd_audit(directory):
    """Audit for accidentally committed secrets."""
    secret_patterns = [
        (r'(?:password|passwd|pwd)\s*[=:]\s*["\']?[\w!@#$%^&*]{8,}', "password"),
        (r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']?[\w-]{20,}', "API key"),
        (r'(?:secret|token)\s*[=:]\s*["\']?[\w-]{20,}', "secret/token"),
        (r'sk-[a-zA-Z0-9]{20,}', "OpenAI key"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub token"),
        (r'AKIA[0-9A-Z]{16}', "AWS access key"),
    ]
    
    findings = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", "__pycache__"}]
        for fname in files:
            if fname.endswith((".env", ".key", ".pem")): continue  # Expected
            if not fname.endswith((".py", ".js", ".ts", ".go", ".yml", ".yaml", ".json", ".toml", ".md")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath) as f:
                    for i, line in enumerate(f, 1):
                        for pattern, label in secret_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                findings.append({"file": fpath, "line": i, "type": label, "preview": line.strip()[:80]})
            except (UnicodeDecodeError, PermissionError): continue
    
    if findings:
        print(f"🔴 Found {len(findings)} potential secrets!\n")
        for f in findings:
            print(f"  [{f['type']}] {f['file']}:{f['line']}")
            print(f"    {f['preview']}")
    else:
        print("✅ No leaked secrets found.")
    
    return 1 if findings else 0


def main():
    parser = argparse.ArgumentParser(description="Manage .env files")
    sub = parser.add_subparsers(dest="cmd")
    
    c = sub.add_parser("compare"); c.add_argument("file1"); c.add_argument("file2")
    v = sub.add_parser("validate"); v.add_argument("env_file"); v.add_argument("--template", required=True)
    g = sub.add_parser("generate"); g.add_argument("output"); g.add_argument("--from-code", required=True)
    m = sub.add_parser("merge"); m.add_argument("files", nargs="+"); m.add_argument("--output", "-o", required=True)
    a = sub.add_parser("audit"); a.add_argument("directory", default=".")
    
    args = parser.parse_args()
    
    if args.cmd == "compare": cmd_compare(args.file1, args.file2)
    elif args.cmd == "validate": sys.exit(cmd_validate(args.env_file, args.template))
    elif args.cmd == "generate": cmd_generate(args.output, args.from_code)
    elif args.cmd == "merge":
        merged = {}
        for f in args.files: merged.update(parse_env(f))
        with open(args.output, "w") as out:
            for k, v in sorted(merged.items()): out.write(f"{k}={v}\n")
        print(f"✅ Merged {len(args.files)} files → {args.output} ({len(merged)} vars)")
    elif args.cmd == "audit": sys.exit(cmd_audit(args.directory))
    else: parser.print_help()


if __name__ == "__main__":
    main()
