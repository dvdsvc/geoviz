"""
Hybrid RAG pipeline v2: Vector search + Knowledge Graph + Structured metadata.

Query flow:
  1. LLM analyzes query → {intent, entities, filters}
  2. Route to retrieval strategies:
     - semantic/vector: embed query → ChromaDB top-k
     - graph_navigate: find entity → traverse graph → get samples
     - graph_relation: temporal/spatial neighbors
     - structured: metadata filter (age range, region, rock type, etc.)
     - hybrid: combine multiple strategies, deduplicate, rank
  3. Gather rich context from graph for each matched sample
  4. LLM formats answer
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from gemini_client import GeminiClient

from sample_loader import load_samples, sample_to_text
from knowledge_graph import KnowledgeGraph
from vector_store import VectorStore


# ── Prompts ─────────────────────────────────────────────────────────────────

QUERY_ANALYSIS_SYSTEM = """\
You are a geological query analyzer. Given a user's question about geochronology samples,
output a JSON object with the query analysis.

CRITICAL: Output ONLY valid JSON, no markdown, no explanation.

Fields in the JSON:
- intent: "semantic" | "graph_navigate" | "graph_relation" | "structured" | "hybrid" | "chat"
  - "semantic": finding similar samples, fuzzy descriptions ("类似张家口组的凝灰岩")
  - "graph_navigate": asking what belongs to what ("丽水盆地有哪些组", "朝川组有什么样品")
  - "graph_relation": asking about related/contemporary samples ("和ZJ66同期的样品")
  - "structured": precise filters on age/region/rock type ("年龄大于150Ma的凝灰岩")
  - "hybrid": combination of above ("华南白垩纪的类似张家口组的样品")
  - "chat": general chat, not a database query
- entities: list of named entities found (formation names, basin names, sample IDs, region names)
- filters: structured filters extracted (only for "structured" or "hybrid" intent):
  - region: one of "华北"/"东北"/"华南"/"西北" or null
  - basin: basin name or null
  - formation: formation name or null
  - rockType: rock type or null
  - age_min / age_max: numeric age in Ma or null
  - datingSystem: dating system or null
  - technique: technique or null
- search_text: a rewritten search query optimized for semantic search (for "semantic" and "hybrid")

Examples:
"丽水盆地有哪些地层组？" → {"intent":"graph_navigate","entities":["丽水盆地"],"filters":null,"search_text":null}
"找类似朝川组凝灰岩的样品" → {"intent":"semantic","entities":["朝川组","凝灰岩"],"filters":null,"search_text":"朝川组 凝灰岩 火山岩"}
"年龄大于150 Ma的华北凝灰岩" → {"intent":"structured","entities":["凝灰岩","华北"],"filters":{"region":"华北","rockType":"凝灰岩","age_min":150},"search_text":null}
"和ZJ66同期同区域的样品有哪些" → {"intent":"graph_relation","entities":["ZJ66"],"filters":null,"search_text":null}
"华南白垩纪类似赤城山组的样品" → {"intent":"hybrid","entities":["华南","赤城山组","白垩纪"],"filters":{"region":"华南","age_min":66,"age_max":145},"search_text":"赤城山组 凝灰岩 白垩纪"}
"""

ANSWER_SYSTEM = """\
You are a geochronology data assistant. Given the user's question, matched samples, and graph context,
compose a clear, concise answer in the SAME language as the question.

Rules:
- ONLY use data from the provided search results below. NEVER fabricate data.
- If no samples found, say so clearly.
- For lists, use bullet points.
- Include sample IDs, ages, locations, rock types.
- Mention graph relationships when relevant (e.g., "这些样品同属XX盆地").
- Keep under 300 words.
"""


# ── Pipeline ─────────────────────────────────────────────────────────────────

class RAGPipelineV2:
    def __init__(self):
        self._gemini_kwargs = dict(
            api_key=os.environ.get("GEMINI_API_KEY", ''),
            model=os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview"),
        )
        self._samples: list[dict] = []
        self._kg: Optional[KnowledgeGraph] = None
        self._vs: Optional[VectorStore] = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._samples = load_samples()
        self._kg = KnowledgeGraph(self._samples)
        self._vs = VectorStore()

        # Index if empty
        if self._vs.count() == 0 and self._samples:
            n = self._vs.index_samples(self._samples)
            print(f"[RAG v2] Indexed {n} samples into vector store")

        self._loaded = True

    def _get_client(self) -> GeminiClient:
        return GeminiClient(**self._gemini_kwargs)

    def _analyze_query(self, query: str) -> dict:
        """LLM analyzes query → structured analysis."""
        resp = self._get_client().chat(
            query,
            system=QUERY_ANALYSIS_SYSTEM,
            temperature=0.1,
            max_tokens=1024,
        )
        raw = resp.strip()
        match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"intent": "chat", "entities": [], "filters": None, "search_text": None}

    def _retrieve_by_intent(self, analysis: dict) -> list[dict]:
        """Execute retrieval based on query intent."""
        intent = analysis.get("intent", "chat")
        entities = analysis.get("entities", [])
        filters = analysis.get("filters") or {}
        search_text = analysis.get("search_text") or ""

        if intent == "chat":
            return []

        results: list[dict] = []
        seen_ids: set[str] = set()

        def add_samples(samples: list[dict]):
            for s in samples:
                sid = s.get("sampleId", "")
                if sid and sid not in seen_ids:
                    seen_ids.add(sid)
                    results.append(s)

        # 1. Vector/semantic search
        if intent in ("semantic", "hybrid") and (search_text or entities):
            query_text = search_text or " ".join(entities)
            if query_text:
                vs_results = self._vs.search(query_text, top_k=15)
                for vr in vs_results:
                    sid = vr["sampleId"]
                    if sid not in seen_ids:
                        sample = self._kg.get_sample(sid)
                        if sample:
                            sample["_match_type"] = "semantic"
                            sample["_score"] = vr.get("distance")
                            add_samples([sample])

        # 2. Graph navigation
        if intent in ("graph_navigate", "graph_relation", "hybrid"):
            for entity in entities:
                # Try as formation
                fm_samples = self._kg.get_samples_by_formation(entity)
                add_samples(fm_samples)

                # Try as basin
                basin_samples = self._kg.get_samples_by_basin(entity)
                add_samples(basin_samples)

                # Try as region
                region_samples = self._kg.get_samples_by_region(entity)
                add_samples(region_samples)

                # Try as sample ID (graph_relation)
                if intent == "graph_relation":
                    temporal = self._kg.get_temporally_near(entity, max_age_diff=10)
                    add_samples(temporal)
                    same_fm = self._kg.get_same_formation_samples(entity)
                    add_samples(same_fm)

        # 3. Structured filters
        if intent in ("structured", "hybrid"):
            filtered = self._apply_filters(filters)
            add_samples(filtered)

        # If no specific intent matched but we have entities, fall back to structured
        if not results and entities:
            for entity in entities:
                for s in self._samples:
                    text = sample_to_text(s)
                    if entity.lower() in text.lower():
                        add_samples([s])

        return results

    def _apply_filters(self, filters: dict) -> list[dict]:
        """Apply structured metadata filters."""
        results = list(self._samples)
        for key in ("region", "basin", "formation", "rockType", "datingSystem", "technique"):
            val = filters.get(key)
            if val:
                results = [s for s in results if val.lower() in str(s.get(key, "")).lower()]

        age_min = filters.get("age_min")
        age_max = filters.get("age_max")
        if age_min is not None:
            results = [s for s in results if s.get("ageMa") is not None and s["ageMa"] >= float(age_min)]
        if age_max is not None:
            results = [s for s in results if s.get("ageMa") is not None and s["ageMa"] <= float(age_max)]

        return results

    def _enrich_with_graph_context(self, samples: list[dict]) -> str:
        """Build rich context string from graph for the matched samples."""
        if not samples:
            return "No matching samples found."

        parts = []
        for s in samples[:15]:
            sid = s.get("sampleId", "")
            age_str = f"{s['ageMa']} Ma ± {s['error']}" if s.get("ageMa") else "无年龄数据"
            match_type = s.get("_match_type", "")
            score_str = f" [相似度: {s['_score']:.4f}]" if s.get("_score") else ""

            parts.append(
                f"- {sid}: {s.get('region','')}·{s.get('basin','')}·{s.get('formation','')}，"
                f"{s.get('rockType','')}，{age_str}，{s.get('technique','')}，"
                f"ref: {s.get('reference','')}{score_str}"
            )

            # Add graph context for top 5
            if len(parts) <= 5:
                ctx = self._kg.get_context_for_sample(sid)
                if ctx:
                    parts.append(f"  {ctx}")

        if len(samples) > 15:
            parts.append(f"... 等共 {len(samples)} 条样品")

        return "\n".join(parts)

    def _format_answer(self, query: str, analysis: dict, samples: list[dict]) -> str:
        """LLM formats the answer."""
        intent = analysis.get("intent", "chat")

        if intent == "chat":
            return "该问题与地质样品数据库无关。你可以问我：\n- 华南地区有哪些凝灰岩样品？\n- 找类似张家口组的样品\n- 丽水盆地有哪些地层组？\n- 年龄大于150Ma的样品有哪些？"

        if not samples:
            return "未在数据库中找到符合条件的样品记录。"

        context = self._enrich_with_graph_context(samples)
        user_msg = f"Question: {query}\n\nSearch Results ({len(samples)} samples matched):\n{context}"

        resp = self._get_client().chat(
            user_msg,
            system=ANSWER_SYSTEM,
            temperature=0.3,
            max_tokens=2048,
        )
        return resp.strip()

    def query(self, nl_query: str) -> dict:
        """
        Full hybrid RAG pipeline.
        Returns {answer, matched_samples, analysis}
        """
        self._ensure_loaded()

        # Step 1: Analyze query
        analysis = self._analyze_query(nl_query)

        # Step 2: Retrieve
        matched = self._retrieve_by_intent(analysis)

        # Step 3: Format answer
        answer = self._format_answer(nl_query, analysis, matched)

        # Clean matched samples for API response
        clean_samples = []
        for s in matched[:20]:
            clean_samples.append({
                "sampleId": s.get("sampleId", ""),
                "region": s.get("region", ""),
                "basin": s.get("basin", ""),
                "formation": s.get("formation", ""),
                "rockType": s.get("rockType", ""),
                "ageMa": s.get("ageMa"),
                "error": s.get("error"),
            })

        return {
            "answer": answer,
            "matched_count": len(matched),
            "matched_samples": clean_samples,
            "analysis": {
                "intent": analysis.get("intent", ""),
                "entities": analysis.get("entities", []),
                "filters": analysis.get("filters"),
            },
        }

    def rebuild_index(self) -> dict:
        """Rebuild the vector index from current samples."""
        self._ensure_loaded()
        self._vs.clear()
        n = self._vs.index_samples(self._samples)
        return {"indexed": n, "total_samples": len(self._samples)}

    def stats(self) -> dict:
        self._ensure_loaded()
        return {
            "samples": len(self._samples),
            "vectors": self._vs.count(),
            "graph": self._kg.summary(),
        }
