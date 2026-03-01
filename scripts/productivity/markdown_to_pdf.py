#!/usr/bin/env python3
"""
Markdown to PDF Converter
=========================
Convert Markdown files to styled PDFs. Supports syntax highlighting,
tables, images, and custom CSS themes.

Usage:
    python markdown_to_pdf.py report.md
    python markdown_to_pdf.py report.md --output report.pdf --theme dark
    python markdown_to_pdf.py *.md --output combined.pdf

Requirements:
    pip install markdown weasyprint pygments
"""

import argparse
import sys
from pathlib import Path

try:
    import markdown
    from markdown.extensions.codehilite import CodeHiliteExtension
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.toc import TocExtension
except ImportError:
    print("Install markdown: pip install markdown")
    sys.exit(1)

try:
    from weasyprint import HTML
except ImportError:
    HTML = None


THEMES = {
    "light": """
        body { font-family: 'Georgia', serif; max-width: 800px; margin: 40px auto; padding: 0 20px;
               color: #333; line-height: 1.7; font-size: 14px; }
        h1 { color: #1a1a2e; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
        h2 { color: #333; margin-top: 2em; }
        h3 { color: #555; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
        pre { background: #f8f8f8; padding: 16px; border-radius: 8px; overflow-x: auto; border: 1px solid #e0e0e0; }
        blockquote { border-left: 4px solid #667eea; margin: 1em 0; padding: 0.5em 1em; color: #555; background: #f9f9ff; }
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
        th { background: #667eea; color: white; }
        tr:nth-child(even) { background: #f9f9f9; }
        a { color: #667eea; }
        img { max-width: 100%; border-radius: 8px; }
    """,
    "dark": """
        body { font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px;
               color: #e0e0e0; background: #1a1a2e; line-height: 1.7; font-size: 14px; }
        h1 { color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
        h2 { color: #aaa; margin-top: 2em; }
        code { background: #2a2a3e; padding: 2px 6px; border-radius: 3px; color: #f0c674; }
        pre { background: #16213e; padding: 16px; border-radius: 8px; overflow-x: auto; }
        blockquote { border-left: 4px solid #667eea; padding: 0.5em 1em; color: #999; background: #16213e; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #333; padding: 8px 12px; }
        th { background: #667eea; color: white; }
        a { color: #667eea; }
        img { max-width: 100%; border-radius: 8px; }
    """,
    "minimal": """
        body { font-family: system-ui, sans-serif; max-width: 700px; margin: 60px auto; padding: 0 20px;
               color: #222; line-height: 1.8; font-size: 15px; }
        h1 { font-weight: 700; }
        code { background: #eee; padding: 2px 4px; border-radius: 2px; }
        pre { background: #f5f5f5; padding: 1em; border-radius: 4px; }
        blockquote { border-left: 3px solid #999; padding-left: 1em; color: #666; }
    """,
}


def md_to_html(md_text: str, theme: str = "light") -> str:
    """Convert Markdown to styled HTML."""
    extensions = [
        "tables",
        "fenced_code",
        "codehilite",
        "toc",
        "smarty",
        "meta",
    ]
    extension_configs = {
        "codehilite": {"css_class": "highlight", "linenums": False},
    }

    html_body = markdown.markdown(md_text, extensions=extensions, extension_configs=extension_configs)
    css = THEMES.get(theme, THEMES["light"])

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body>{html_body}</body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to styled HTML/PDF")
    parser.add_argument("files", nargs="+", help="Markdown files to convert")
    parser.add_argument("--output", help="Output filename")
    parser.add_argument("--theme", choices=list(THEMES.keys()), default="light")
    parser.add_argument("--format", choices=["html", "pdf"], default="html",
                        help="Output format (pdf requires weasyprint)")
    args = parser.parse_args()

    # Combine all input files
    combined_md = ""
    for filepath in args.files:
        p = Path(filepath)
        if not p.exists():
            print(f"⚠ Skipping {filepath} (not found)")
            continue
        combined_md += p.read_text(encoding="utf-8") + "\n\n---\n\n"

    if not combined_md.strip():
        print("No content to convert.")
        sys.exit(1)

    html = md_to_html(combined_md, args.theme)

    # Determine output
    default_name = Path(args.files[0]).stem if len(args.files) == 1 else "combined"
    if args.format == "pdf":
        if HTML is None:
            print("PDF output requires weasyprint: pip install weasyprint")
            sys.exit(1)
        out_path = Path(args.output or f"{default_name}.pdf")
        HTML(string=html).write_pdf(str(out_path))
    else:
        out_path = Path(args.output or f"{default_name}.html")
        out_path.write_text(html)

    print(f"✅ {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
