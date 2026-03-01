#!/usr/bin/env python3
"""
Chat with Your Documents (RAG-lite)
====================================
Load documents from a directory, chunk them, and chat using semantic search.
No vector DB required — uses in-memory cosine similarity with sentence-transformers.

Usage:
    python chat_with_docs.py ./docs/
    python chat_with_docs.py ./docs/ --provider anthropic
    python chat_with_docs.py ./docs/ --no-interactive --query "What is the refund policy?"

Environment:
    OPENAI_API_KEY    — for OpenAI
    ANTHROPIC_API_KEY — for Anthropic

Requirements:
    pip install httpx sentence-transformers numpy
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

try:
    import httpx
    import numpy as np
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Install dependencies: pip install httpx sentence-transformers numpy")
    sys.exit(1)


def load_documents(directory: Path) -> list[dict]:
    """Load text files and split into chunks."""
    chunks = []
    for f in sorted(directory.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() not in (".txt", ".md", ".csv", ".json", ".py", ".js", ".html"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Split into ~500 char chunks with overlap
        chunk_size = 500
        overlap = 100
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size].strip()
            if len(chunk) > 50:
                chunks.append({"text": chunk, "source": str(f.relative_to(directory)), "offset": i})
    return chunks


def build_index(chunks: list[dict], model: SentenceTransformer) -> np.ndarray:
    """Build embedding index for all chunks."""
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return embeddings


def search(query: str, chunks: list[dict], embeddings: np.ndarray, 
           model: SentenceTransformer, top_k: int = 5) -> list[dict]:
    """Find most relevant chunks for a query."""
    q_emb = model.encode([query], normalize_embeddings=True)
    scores = (embeddings @ q_emb.T).flatten()
    top_indices = scores.argsort()[-top_k:][::-1]
    results = []
    for idx in top_indices:
        results.append({
            "text": chunks[idx]["text"],
            "source": chunks[idx]["source"],
            "score": float(scores[idx]),
        })
    return results


async def ask_llm(client: httpx.AsyncClient, query: str, context: str,
                  provider: str, api_key: str) -> str:
    """Ask LLM with retrieved context."""
    system = (
        "Answer the user's question based on the provided context. "
        "If the context doesn't contain enough information, say so. "
        "Cite the source file when relevant."
    )
    user_msg = f"Context:\n{context}\n\nQuestion: {query}"

    if provider == "openai":
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
                "max_tokens": 500,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    else:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "system": system,
                "messages": [{"role": "user", "content": user_msg}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


async def main():
    parser = argparse.ArgumentParser(description="Chat with your documents using RAG")
    parser.add_argument("directory", help="Directory with documents")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--query", help="Single query (non-interactive)")
    parser.add_argument("--no-interactive", action="store_true")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    parser.add_argument("--embed-model", default="all-MiniLM-L6-v2", help="Embedding model")
    args = parser.parse_args()

    env_key = "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
    api_key = os.environ.get(env_key)
    if not api_key:
        print(f"Error: Set {env_key}")
        sys.exit(1)

    # Load docs
    doc_dir = Path(args.directory)
    print(f"📂 Loading documents from {doc_dir}...")
    chunks = load_documents(doc_dir)
    if not chunks:
        print("No documents found.")
        sys.exit(1)
    print(f"   {len(chunks)} chunks from {len(set(c['source'] for c in chunks))} files")

    # Build index
    print(f"🔍 Building search index ({args.embed_model})...")
    model = SentenceTransformer(args.embed_model)
    embeddings = build_index(chunks, model)
    print(f"   ✓ Index ready ({embeddings.shape})")

    async with httpx.AsyncClient() as client:
        async def answer(query: str):
            results = search(query, chunks, embeddings, model, args.top_k)
            context = "\n\n---\n\n".join(
                f"[{r['source']}] (relevance: {r['score']:.2f})\n{r['text']}" 
                for r in results
            )
            return await ask_llm(client, query, context, args.provider, api_key)

        if args.query or args.no_interactive:
            q = args.query or input("Question: ")
            print(f"\n{await answer(q)}")
        else:
            print("\n💬 Chat mode — type 'quit' to exit\n")
            while True:
                try:
                    q = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if q.lower() in ("quit", "exit", "q"):
                    break
                if not q:
                    continue
                reply = await answer(q)
                print(f"\n🤖 {reply}\n")

    print("Bye!")


if __name__ == "__main__":
    asyncio.run(main())
