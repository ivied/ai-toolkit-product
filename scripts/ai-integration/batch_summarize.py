#!/usr/bin/env python3
"""
Batch Document Summarizer
========================
Summarize multiple files (txt, md, pdf) in a directory using OpenAI or Anthropic.
Outputs individual summaries + a combined executive summary.

Usage:
    python batch_summarize.py ./documents/ --provider openai --output summaries/
    python batch_summarize.py ./reports/ --provider anthropic --max-tokens 500

Environment:
    OPENAI_API_KEY    — for OpenAI provider
    ANTHROPIC_API_KEY — for Anthropic provider
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


PROVIDERS = {
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "env": "OPENAI_API_KEY",
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-haiku-4-5-20251001",
        "env": "ANTHROPIC_API_KEY",
    },
}


async def summarize_openai(client: httpx.AsyncClient, text: str, api_key: str, model: str, max_tokens: int) -> str:
    resp = await client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "Summarize the following document concisely. Focus on key points, decisions, and action items."},
                {"role": "user", "content": text[:15000]},  # Trim to avoid token limits
            ],
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


async def summarize_anthropic(client: httpx.AsyncClient, text: str, api_key: str, model: str, max_tokens: int) -> str:
    resp = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": f"Summarize the following document concisely. Focus on key points, decisions, and action items.\n\n{text[:15000]}"},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


async def process_file(filepath: Path) -> str | None:
    """Read a file and return its text content."""
    suffix = filepath.suffix.lower()
    if suffix in (".txt", ".md", ".csv", ".json", ".log"):
        return filepath.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(filepath))
            return "\n".join(page.get_text() for page in doc)
        except ImportError:
            print(f"  ⚠ Skipping {filepath.name} (install PyMuPDF for PDF support: pip install PyMuPDF)")
            return None
    else:
        print(f"  ⚠ Skipping {filepath.name} (unsupported format)")
        return None


async def main():
    parser = argparse.ArgumentParser(description="Batch-summarize documents using AI")
    parser.add_argument("directory", help="Directory containing documents")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--model", help="Override model name")
    parser.add_argument("--output", default="summaries", help="Output directory")
    parser.add_argument("--max-tokens", type=int, default=300, help="Max tokens per summary")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent API calls")
    args = parser.parse_args()

    provider = PROVIDERS[args.provider]
    api_key = os.environ.get(provider["env"])
    if not api_key:
        print(f"Error: Set {provider['env']} environment variable")
        sys.exit(1)

    model = args.model or provider["model"]
    input_dir = Path(args.directory)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(f for f in input_dir.iterdir() if f.is_file())
    print(f"Found {len(files)} files in {input_dir}")

    summarize = summarize_openai if args.provider == "openai" else summarize_anthropic
    sem = asyncio.Semaphore(args.concurrency)
    summaries = {}

    async with httpx.AsyncClient() as client:
        async def process_one(f: Path):
            async with sem:
                text = await process_file(f)
                if not text or len(text.strip()) < 50:
                    return
                print(f"  📝 Summarizing {f.name}...")
                try:
                    summary = await summarize(client, text, api_key, model, args.max_tokens)
                    summaries[f.name] = summary
                    out_file = output_dir / f"{f.stem}_summary.md"
                    out_file.write_text(f"# Summary: {f.name}\n\n{summary}\n")
                    print(f"  ✓ {f.name} → {out_file.name}")
                except Exception as e:
                    print(f"  ✗ {f.name}: {e}")

        await asyncio.gather(*(process_one(f) for f in files))

    # Executive summary
    if summaries:
        combined = "\n\n".join(f"## {name}\n{s}" for name, s in sorted(summaries.items()))
        exec_file = output_dir / "EXECUTIVE_SUMMARY.md"
        exec_file.write_text(f"# Executive Summary\n\nSummarized {len(summaries)} documents.\n\n{combined}\n")
        print(f"\n✅ Done! {len(summaries)} summaries → {output_dir}/")
        print(f"   Executive summary: {exec_file}")
    else:
        print("\n⚠ No documents were summarized.")


if __name__ == "__main__":
    asyncio.run(main())
