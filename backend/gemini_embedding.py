"""
Google Gemini embedding client — batch embed via REST API.
Uses gemini-embedding-2, dimension auto-detected on first call.
"""

import hashlib
import json
import os
import sqlite3
import time
import urllib.request
from pathlib import Path
from typing import Optional

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    '',
)

EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
# Auto-detected on first embed call; override with env if known
EMBEDDING_DIM = int(os.environ.get("GEMINI_EMBEDDING_DIM", "0")) or None

API_BASE = "https://generativelanguage.googleapis.com/v1beta"

CACHE_DB = os.environ.get(
    "GEMINI_EMBED_CACHE_DB",
    str(Path(__file__).resolve().parent / "embedding_cache.sqlite"),
)
CACHE_TTL = int(os.environ.get("GEMINI_EMBED_CACHE_TTL", "0"))  # 0 = never expire


def _init_cache(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS embed_cache (
            text_hash TEXT PRIMARY KEY,
            embedding TEXT NOT NULL,
            model TEXT,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


_cache_conn: Optional[sqlite3.Connection] = None


def _get_cache_conn() -> sqlite3.Connection:
    global _cache_conn
    if _cache_conn is None:
        _cache_conn = _init_cache(CACHE_DB)
    return _cache_conn


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


_detected_dim: Optional[int] = None


def get_dimension() -> int:
    """Return embedding dimension, auto-detecting on first call."""
    global _detected_dim
    if _detected_dim is not None:
        return _detected_dim
    if EMBEDDING_DIM is not None:
        _detected_dim = EMBEDDING_DIM
        return _detected_dim
    # Auto-detect
    vec = embed_batch(["dimension probe"], use_cache=False)[0]
    _detected_dim = len(vec)
    return _detected_dim


def embed_batch(texts: list[str], model: str = EMBEDDING_MODEL, use_cache: bool = True) -> list[list[float]]:
    """
    Embed a batch of texts. Returns list of embedding vectors.
    Max 100 texts per call.
    """
    model_path = f"models/{model}"
    results: list[Optional[list[float]]] = [None] * len(texts)
    uncached_indices: list[int] = []
    uncached_texts: list[str] = []

    if use_cache:
        conn = _get_cache_conn()
        for i, text in enumerate(texts):
            h = _text_hash(text)
            row = conn.execute(
                "SELECT embedding FROM embed_cache WHERE text_hash = ?", (h,)
            ).fetchone()
            if row is not None:
                results[i] = json.loads(row[0])
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
    else:
        uncached_indices = list(range(len(texts)))
        uncached_texts = list(texts)

    if uncached_texts:
        url = f"{API_BASE}/{model_path}:batchEmbedContents?key={GEMINI_API_KEY}"
        requests_payload = [
            {"model": model_path, "content": {"parts": [{"text": t}]}}
            for t in uncached_texts
        ]
        payload = json.dumps({"requests": requests_payload}).encode()

        for attempt in range(5):
            try:
                req = urllib.request.Request(
                    url, data=payload, headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read())
                embeds = result["embeddings"]
                for j, emb in enumerate(embeds):
                    vec = emb["values"]
                    idx = uncached_indices[j]
                    results[idx] = vec
                    if use_cache:
                        conn = _get_cache_conn()
                        conn.execute(
                            "INSERT OR REPLACE INTO embed_cache (text_hash, embedding, model, created_at) VALUES (?, ?, ?, ?)",
                            (_text_hash(uncached_texts[j]), json.dumps(vec), model, time.time()),
                        )
                        conn.commit()
                break
            except Exception as e:
                err_msg = str(e)
                if attempt == 4:
                    raise
                wait = (2 ** attempt) + (5 if "429" in err_msg else 0)
                print(f"[Embed] attempt {attempt+1}/5 failed: {e}, retry in {wait}s")
                time.sleep(wait)

    return [r for r in results if r is not None]  # type: ignore


def embed_single(text: str, model: str = EMBEDDING_MODEL) -> list[float]:
    """Embed a single text."""
    return embed_batch([text], model=model)[0]


def embed_with_cache(texts: list[str], model: str = EMBEDDING_MODEL) -> list[list[float]]:
    """Embed texts, using local SQLite cache."""
    return embed_batch(texts, model=model, use_cache=True)
