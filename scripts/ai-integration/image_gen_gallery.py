#!/usr/bin/env python3
"""
AI Image Generation Gallery
===========================
Generate multiple images from prompts and create an HTML gallery.
Supports OpenAI DALL-E and Stability AI.

Usage:
    python image_gen_gallery.py --prompts prompts.txt --output gallery/
    python image_gen_gallery.py --prompt "a sunset over mountains" --variations 4
    echo "cyberpunk city\nfantasy castle" | python image_gen_gallery.py --output art/

Environment:
    OPENAI_API_KEY — for DALL-E
"""

import argparse
import asyncio
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


async def generate_dalle(client: httpx.AsyncClient, prompt: str, api_key: str, 
                          model: str = "dall-e-3", size: str = "1024x1024") -> bytes:
    """Generate image via OpenAI DALL-E."""
    resp = await client.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json",
        },
        timeout=120,
    )
    resp.raise_for_status()
    return base64.b64decode(resp.json()["data"][0]["b64_json"])


def create_gallery_html(images: list[dict], output_dir: Path) -> Path:
    """Create a responsive HTML gallery."""
    cards = ""
    for img in images:
        cards += f"""
        <div class="card">
            <img src="{img['filename']}" alt="{img['prompt']}" loading="lazy">
            <p>{img['prompt']}</p>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Image Gallery — {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #0a0a0a; color: #fff; font-family: system-ui, sans-serif; padding: 2rem; }}
        h1 {{ text-align: center; margin-bottom: 2rem; font-size: 2rem; 
              background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; 
              -webkit-text-fill-color: transparent; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem; }}
        .card {{ background: #1a1a2e; border-radius: 12px; overflow: hidden; transition: transform 0.2s; }}
        .card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 30px rgba(102, 126, 234, 0.2); }}
        .card img {{ width: 100%; aspect-ratio: 1; object-fit: cover; }}
        .card p {{ padding: 1rem; font-size: 0.9rem; color: #aaa; }}
        .meta {{ text-align: center; color: #555; margin-top: 2rem; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <h1>🎨 AI Image Gallery</h1>
    <div class="grid">{cards}</div>
    <p class="meta">Generated {len(images)} images on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</body>
</html>"""

    gallery_path = output_dir / "index.html"
    gallery_path.write_text(html)
    return gallery_path


async def main():
    parser = argparse.ArgumentParser(description="Generate AI images and create a gallery")
    parser.add_argument("--prompt", help="Single prompt")
    parser.add_argument("--prompts", help="File with prompts (one per line)")
    parser.add_argument("--output", default="gallery", help="Output directory")
    parser.add_argument("--model", default="dall-e-3", choices=["dall-e-3", "dall-e-2"])
    parser.add_argument("--size", default="1024x1024", help="Image size")
    parser.add_argument("--variations", type=int, default=1, help="Variations per prompt")
    parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent requests")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: Set OPENAI_API_KEY environment variable")
        sys.exit(1)

    # Collect prompts
    prompts = []
    if args.prompt:
        prompts.append(args.prompt)
    elif args.prompts:
        prompts = [l.strip() for l in Path(args.prompts).read_text().splitlines() if l.strip()]
    elif not sys.stdin.isatty():
        prompts = [l.strip() for l in sys.stdin if l.strip()]
    else:
        print("Provide --prompt, --prompts file, or pipe prompts via stdin")
        sys.exit(1)

    # Expand variations
    all_prompts = prompts * args.variations
    print(f"Generating {len(all_prompts)} images...")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(args.concurrency)
    images = []

    async with httpx.AsyncClient() as client:
        async def gen(prompt: str, idx: int):
            async with sem:
                print(f"  🎨 [{idx+1}/{len(all_prompts)}] {prompt[:60]}...")
                try:
                    img_data = await generate_dalle(client, prompt, api_key, args.model, args.size)
                    filename = f"img_{idx:03d}.png"
                    (output_dir / filename).write_bytes(img_data)
                    images.append({"prompt": prompt, "filename": filename})
                    print(f"  ✓ {filename}")
                except Exception as e:
                    print(f"  ✗ Error: {e}")

        await asyncio.gather(*(gen(p, i) for i, p in enumerate(all_prompts)))

    if images:
        gallery = create_gallery_html(sorted(images, key=lambda x: x["filename"]), output_dir)
        # Save metadata
        meta = {"generated": datetime.now().isoformat(), "images": images}
        (output_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
        print(f"\n✅ {len(images)} images generated → {output_dir}/")
        print(f"   Gallery: {gallery}")
    else:
        print("\n⚠ No images generated.")


if __name__ == "__main__":
    asyncio.run(main())
