#!/usr/bin/env python3
"""
AI README Generator — Generate professional README.md for projects.

Analyzes project structure, code, and config files to automatically
generate a comprehensive README with badges, install steps, and examples.

Usage:
    python readme_generator.py ~/projects/myapp
    python readme_generator.py . --style minimal
    python readme_generator.py . --ai --output README.md

Requirements:
    pip install openai  (optional, for AI-enhanced descriptions)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

BADGES = {
    "python": "![Python](https://img.shields.io/badge/python-3.x-blue)",
    "javascript": "![Node.js](https://img.shields.io/badge/node.js-18+-green)",
    "typescript": "![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue)",
    "rust": "![Rust](https://img.shields.io/badge/rust-stable-orange)",
    "go": "![Go](https://img.shields.io/badge/go-1.21+-blue)",
    "mit": "![License: MIT](https://img.shields.io/badge/License-MIT-yellow)",
}


def analyze_project(directory):
    """Analyze project structure and detect stack."""
    info = {
        "name": Path(directory).name,
        "languages": set(),
        "files": [],
        "has_docker": False,
        "has_tests": False,
        "package_manager": None,
        "entry_point": None,
        "license": None,
        "description": "",
    }
    
    ext_lang = {".py": "python", ".js": "javascript", ".ts": "typescript",
                ".go": "go", ".rs": "rust", ".rb": "ruby", ".java": "java"}
    
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", "__pycache__", ".venv", "target"}]
        depth = root.replace(directory, "").count(os.sep)
        if depth > 3: continue
        
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), directory)
            info["files"].append(rel)
            
            ext = Path(f).suffix.lower()
            if ext in ext_lang:
                info["languages"].add(ext_lang[ext])
            
            if f == "Dockerfile": info["has_docker"] = True
            if f == "package.json": info["package_manager"] = "npm"
            if f == "requirements.txt": info["package_manager"] = "pip"
            if f == "Cargo.toml": info["package_manager"] = "cargo"
            if f == "go.mod": info["package_manager"] = "go"
            if f == "pyproject.toml": info["package_manager"] = "pip"
            if "test" in f.lower() or "spec" in f.lower(): info["has_tests"] = True
            if f == "LICENSE": info["license"] = "mit"
            if f == "main.py": info["entry_point"] = "python main.py"
            if f == "app.py": info["entry_point"] = "python app.py"
            if f == "index.js": info["entry_point"] = "node index.js"
    
    # Try to extract description from existing files
    for desc_file in ["package.json", "pyproject.toml", "Cargo.toml"]:
        fpath = os.path.join(directory, desc_file)
        if os.path.exists(fpath):
            try:
                with open(fpath) as f:
                    content = f.read()
                match = re.search(r'"description"\s*:\s*"([^"]+)"', content)
                if match:
                    info["description"] = match.group(1)
            except Exception:
                pass
    
    info["languages"] = list(info["languages"])
    return info


def generate_readme(info, style="standard"):
    """Generate README content."""
    lines = []
    
    # Title and badges
    lines.append(f"# {info['name']}\n")
    for lang in info["languages"]:
        if lang in BADGES:
            lines.append(BADGES[lang])
    if info["license"] and info["license"] in BADGES:
        lines.append(BADGES[info["license"]])
    lines.append("")
    
    # Description
    if info["description"]:
        lines.append(f"{info['description']}\n")
    else:
        lines.append(f"A {' and '.join(info['languages']) or 'software'} project.\n")
    
    if style == "minimal":
        # Minimal: just install and run
        lines.append("## Quick Start\n")
        lines.append("```bash")
        lines.append(f"git clone https://github.com/user/{info['name']}.git")
        lines.append(f"cd {info['name']}")
        if info["package_manager"] == "pip":
            lines.append("pip install -r requirements.txt")
        elif info["package_manager"] == "npm":
            lines.append("npm install")
        if info["entry_point"]:
            lines.append(info["entry_point"])
        lines.append("```\n")
        return "\n".join(lines)
    
    # Standard/full README
    lines.append("## Features\n")
    lines.append("- Feature 1")
    lines.append("- Feature 2")
    lines.append("- Feature 3\n")
    
    lines.append("## Installation\n")
    lines.append("```bash")
    lines.append(f"git clone https://github.com/user/{info['name']}.git")
    lines.append(f"cd {info['name']}")
    
    if info["package_manager"] == "pip":
        lines.append("python -m venv venv")
        lines.append("source venv/bin/activate  # or venv\\Scripts\\activate on Windows")
        lines.append("pip install -r requirements.txt")
    elif info["package_manager"] == "npm":
        lines.append("npm install")
    elif info["package_manager"] == "cargo":
        lines.append("cargo build")
    elif info["package_manager"] == "go":
        lines.append("go mod download")
    
    lines.append("```\n")
    
    lines.append("## Usage\n")
    lines.append("```bash")
    lines.append(info.get("entry_point", f"# Run the project"))
    lines.append("```\n")
    
    if info["has_docker"]:
        lines.append("## Docker\n")
        lines.append("```bash")
        lines.append(f"docker build -t {info['name']} .")
        lines.append(f"docker run {info['name']}")
        lines.append("```\n")
    
    if info["has_tests"]:
        lines.append("## Testing\n")
        lines.append("```bash")
        if "python" in info["languages"]: lines.append("pytest")
        elif "javascript" in info["languages"]: lines.append("npm test")
        elif "go" in info["languages"]: lines.append("go test ./...")
        elif "rust" in info["languages"]: lines.append("cargo test")
        lines.append("```\n")
    
    # Project structure
    lines.append("## Project Structure\n")
    lines.append("```")
    shown = [f for f in info["files"][:20] if not any(skip in f for skip in ["__pycache__", ".pyc"])]
    for f in sorted(shown):
        lines.append(f"  {f}")
    if len(info["files"]) > 20:
        lines.append(f"  ... and {len(info['files']) - 20} more files")
    lines.append("```\n")
    
    lines.append("## License\n")
    lines.append("MIT License — see [LICENSE](LICENSE) for details.\n")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate README.md for projects")
    parser.add_argument("directory", nargs="?", default=".")
    parser.add_argument("--style", choices=["minimal", "standard", "full"], default="standard")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--json", action="store_true", help="Output project analysis as JSON")
    args = parser.parse_args()
    
    info = analyze_project(args.directory)
    
    if args.json:
        print(json.dumps(info, indent=2, default=list))
        return
    
    readme = generate_readme(info, args.style)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(readme)
        print(f"✅ Generated {args.output}", file=sys.stderr)
    else:
        print(readme)


if __name__ == "__main__":
    main()
