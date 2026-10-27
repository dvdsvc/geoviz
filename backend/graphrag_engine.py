"""
GraphRAG Engine — knowledge graph query for geo-viz backend.

Loads the pre-built graph, communities, and reports from demo_graphrag.py output.
Provides global_search (community-level) and local_search (node-level) queries.
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path

# ── Path: connect to geochron_graphrag project ──

_GRAPHRAG_DIR = Path(os.getenv("GEOVIZ_GRAPHRAG_DIR", str(Path(__file__).resolve().parents[1] / "data/private/graphrag")))
_GRAPHRAG_OUTPUT = _GRAPHRAG_DIR / "graphrag_output"
sys.path.insert(0, str(_GRAPHRAG_DIR))

# ── LLM config (matching demo_graphrag.py) ──

import os

_LLM_CONFIG = {
    "api_key": os.environ.get(
        "DEEPSEEK_API_KEY", ''
    ),
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
}

_EMBEDDING_CONFIG = {
    "api_key": os.environ.get(
        "GEMINI_API_KEY", ''
    ),
    "model": "models/gemini-embedding-2",
}


# ═══════════════════════════════════════════════════════════════


def _llm(system: str, prompt: str, max_tokens: int = 1024) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=_LLM_CONFIG["api_key"], base_url=_LLM_CONFIG["base_url"])
    resp = client.chat.completions.create(
        model=_LLM_CONFIG["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def _embed(text: str) -> list[float]:
    from google import genai

    client = genai.Client(api_key=_EMBEDDING_CONFIG["api_key"])
    result = client.models.embed_content(
        model=_EMBEDDING_CONFIG["model"], contents=text
    )
    return result.embeddings[0].values


def _cosine_sim(a: list[float], b: list[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


# ═══════════════════════════════════════════════════════════════


class GraphRAGEngine:
    """Query engine wrapping the pre-built GraphRAG knowledge graph."""

    def __init__(self):
        self._graph = None
        self._communities: dict = {}
        self._reports: list[dict] = []
        self._report_embeddings: list[list[float] | None] = []
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        import networkx as nx

        graph_file = _GRAPHRAG_OUTPUT / "graph.json"
        comm_file = _GRAPHRAG_OUTPUT / "communities.json"
        reports_file = _GRAPHRAG_OUTPUT / "community_reports.json"

        if not graph_file.exists():
            raise FileNotFoundError(
                f"Graph not found at {graph_file}. Run demo_graphrag.py --build first."
            )

        self._graph = nx.node_link_graph(
            json.loads(graph_file.read_text()), edges="edges"
        )
        self._communities = json.loads(comm_file.read_text())
        self._reports = json.loads(reports_file.read_text())

        # Pre-compute report embeddings
        for report in self._reports:
            text = (
                f"盆地: {' '.join(report.get('basins', [])[:5])}. "
                f"地层: {' '.join(report.get('formations', [])[:5])}. "
                f"岩性: {' '.join(report.get('rock_types', [])[:5])}. "
                f"年龄: {report['age_range']}. "
                f"摘要: {report['summary']}"
            )
            try:
                emb = _embed(text)
            except Exception:
                emb = None
            self._report_embeddings.append(emb)

        self._loaded = True

    def stats(self) -> dict:
        """Return graph statistics."""
        self._ensure_loaded()
        from collections import Counter

        kind_counts = Counter(
            self._graph.nodes[n].get("kind", "?") for n in self._graph.nodes()
        )
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
            "node_types": dict(kind_counts),
            "communities": len(self._reports),
        }

    def global_search(self, question: str) -> dict:
        """Global search: match community reports → LLM answer."""
        self._ensure_loaded()

        # Hybrid scoring: embedding + keyword
        try:
            q_emb = _embed(question)
            sem_scores = [
                _cosine_sim(q_emb, e) if e else 0.0
                for e in self._report_embeddings
            ]
        except Exception:
            sem_scores = [0.0] * len(self._reports)

        q_lower = question.lower()
        kw_scores = [
            sum(
                1
                for w in q_lower.split()
                if len(w) >= 2
                and w in json.dumps(r, ensure_ascii=False).lower()
            )
            for r in self._reports
        ]

        max_sem = max(sem_scores) if sem_scores else 1
        max_kw = max(kw_scores) if kw_scores else 1
        hybrid = [
            0.6 * (s / max_sem) + 0.4 * (k / max_kw) if max_sem > 0 and max_kw > 0 else 0
            for s, k in zip(sem_scores, kw_scores)
        ]
        ranked = sorted(enumerate(hybrid), key=lambda x: -x[1])

        top = [self._reports[i] for i, _ in ranked[:3] if _ > 0.05]
        if not top:
            top = self._reports[:2]

        context = "\n\n".join(
            f"社区 {r['community_id']} ({r['sample_count']} 样品, "
            f"{r['age_range']}):\n{r['summary']}"
            for r in top
        )

        system = "你是地质年代学专家。根据图谱社区报告回答用户问题，中文回答，简洁准确。"
        prompt = f"问题: {question}\n\n相关社区报告:\n{context}"

        answer = _llm(system, prompt, max_tokens=1024)

        return {
            "answer": answer,
            "matched_communities": [
                {
                    "community_id": r["community_id"],
                    "sample_count": r["sample_count"],
                    "age_range": r["age_range"],
                    "basins": r.get("basins", []),
                    "summary": r["summary"],
                }
                for r in top
            ],
            "total_communities": len(self._reports),
            "query_type": "global",
        }

    def local_search(self, sample_id: str) -> dict:
        """Local search: graph traversal around a specific sample."""
        self._ensure_loaded()

        if sample_id not in self._graph:
            return {"error": f"Sample not found: {sample_id}", "query_type": "local"}

        node = self._graph.nodes[sample_id]
        if node.get("kind") != "Sample":
            return {"error": f"Node {sample_id} is not a Sample", "query_type": "local"}

        # Collect 2-hop neighbors
        neighbors = []
        for neighbor in self._graph.neighbors(sample_id):
            info = self._graph.nodes[neighbor]
            neighbors.append(
                {
                    "id": neighbor,
                    "kind": info.get("kind", "?"),
                    "relation": info.get("relation", ""),
                    "age_ma": info.get("age_ma"),
                    "technique": info.get("technique"),
                    "mineral": info.get("mineral"),
                    "annotation": info.get("annotation"),
                }
            )

        # Also include same-community samples
        comm_id = self._communities.get(sample_id)
        related_samples = []
        if comm_id is not None:
            for nid, cid in self._communities.items():
                if cid == comm_id and nid != sample_id:
                    info = self._graph.nodes.get(nid, {})
                    if info.get("kind") == "Sample":
                        related_samples.append(
                            {
                                "id": nid,
                                "basin": info.get("basin"),
                                "formation": info.get("formation"),
                                "rock_type": info.get("rock_type"),
                            }
                        )

        # LLM summary
        context = (
            f"样品: {sample_id}\n"
            + "\n".join(
                f"- {n['kind']}: {n['id']} ({n.get('age_ma','?')} Ma, "
                f"{n.get('technique','')}, {n.get('mineral','')})"
                for n in neighbors[:20]
            )
        )
        if related_samples:
            context += (
                f"\n\n同社区 ({comm_id}) 相关样品: "
                + ", ".join(s["id"] for s in related_samples[:15])
            )

        system = "你是地质年代学专家。根据样品图谱数据回答，中文，简洁。"
        prompt = f"请总结这个样品的关键信息:\n\n{context}"
        answer = _llm(system, prompt, max_tokens=800)

        return {
            "answer": answer,
            "sample_id": sample_id,
            "community_id": comm_id,
            "neighbors": neighbors,
            "related_samples": related_samples,
            "query_type": "local",
        }


# Singleton
engine = GraphRAGEngine()
