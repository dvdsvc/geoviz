"""
ChromaDB vector store for geological samples.
Uses Gemini embedding for semantic search.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from gemini_embedding import embed_batch, get_dimension, EMBEDDING_MODEL
from sample_loader import sample_to_text

COLLECTION_NAME = "geo_samples"
import os
PERSIST_DIR = os.getenv("GEOVIZ_VECTOR_DIR", str(Path(__file__).resolve().parent / "chroma_vectors"))


class VectorStore:
    def __init__(self, persist_dir: str = PERSIST_DIR):
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            dim = get_dimension()
            try:
                self._collection = self._client.get_collection(COLLECTION_NAME)
            except Exception:
                self._collection = self._client.create_collection(
                    name=COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine", "dimension": dim},
                )
        return self._collection

    def index_samples(self, samples: list[dict], batch_size: int = 10) -> int:
        """Embed and index all samples. Returns count of indexed samples."""
        col = self._collection or self._get_or_create_collection()

        # Build text representations
        texts = []
        ids = []
        metadatas = []

        # Detect duplicate sampleIds; if duplicated, suffix with age to disambiguate
        from collections import Counter as _Counter
        sid_counts = _Counter(s["sampleId"] for s in samples)
        dup_sids = {k for k, v in sid_counts.items() if v > 1}

        for s in samples:
            sid = s["sampleId"]
            if sid in dup_sids:
                age = s.get("ageMa")
                age_suffix = f"_{age}" if age is not None else ""
                sid = f"{sid}{age_suffix}"
            texts.append(sample_to_text(s))
            ids.append(sid)
            metadatas.append({
                "sampleId": sid,
                "region": s.get("region", ""),
                "basin": s.get("basin", ""),
                "formation": s.get("formation", ""),
                "rockType": s.get("rockType", ""),
                "ageMa": str(s.get("ageMa", "")) if s.get("ageMa") is not None else "",
            })

        # Batch embed (small batches + delay to avoid 429 rate limit)
        import time as _time
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embs = embed_batch(batch)
            all_embeddings.extend(embs)
            if i + batch_size < len(texts):
                _time.sleep(2)

        # Upsert into ChromaDB
        col.upsert(
            ids=ids,
            embeddings=all_embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        return len(ids)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Semantic search. Returns list of {sampleId, distance, metadata}."""
        col = self.collection
        query_emb = embed_batch([query])[0]
        results = col.query(query_embeddings=[query_emb], n_results=top_k)
        items = []
        if results["ids"] and results["ids"][0]:
            for i, sid in enumerate(results["ids"][0]):
                dist = results["distances"][0][i] if results["distances"] else None
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                items.append({
                    "sampleId": sid,
                    "distance": round(dist, 4) if dist is not None else None,
                    "metadata": meta,
                })
        return items

    def search_similar_to_sample(self, sample_id: str, top_k: int = 10) -> list[dict]:
        """Find samples similar to a given sample (by its text representation)."""
        col = self.collection
        # Get the stored embedding for this sample
        result = col.get(ids=[sample_id], include=["embeddings"])
        if not result["embeddings"]:
            return []
        emb = result["embeddings"][0]
        results = col.query(query_embeddings=[emb], n_results=top_k + 1)
        items = []
        if results["ids"] and results["ids"][0]:
            for i, sid in enumerate(results["ids"][0]):
                if sid == sample_id:
                    continue
                dist = results["distances"][0][i] if results["distances"] else None
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                items.append({
                    "sampleId": sid,
                    "distance": round(dist, 4) if dist is not None else None,
                    "metadata": meta,
                })
        return items[:top_k]

    def _get_or_create_collection(self):
        dim = get_dimension()
        try:
            return self._client.get_collection(COLLECTION_NAME)
        except Exception:
            return self._client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine", "dimension": dim},
            )

    def clear(self):
        try:
            self._client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self._collection = None

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0
