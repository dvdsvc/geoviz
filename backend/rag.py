"""
RAG pipeline for GeoViz:
  NL query → MiMo LLM → structured filter → data search → MiMo LLM → natural language answer
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# Add workspace root to path so we can reuse mimo_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from mimo_client import MiMoClient

from samples_data import SAMPLES

# ── Prompts ─────────────────────────────────────────────────────────────────

QUERY_SYSTEM = """\
You are a database query parser for a geological sample database containing 20 geochronology samples.
Convert the user's question into a JSON filter object to search this database.

CRITICAL RULES:
- You are ONLY a query parser. You do NOT answer questions yourself.
- When the user asks about "samples" (样品/标本), "data" (数据), asks "which/what" (有哪些/是什么),
  or mentions ANY region/basin/formation/rock type/age — it is ALWAYS a database query (intent="query").
- If the question asks about geological concepts, stratigraphy, or sample analysis that COULD relate to the database,
  use intent="query" with an empty filter to return all samples.
- ONLY use intent="none" for completely unrelated questions (e.g. "what's the weather?", "tell me a joke").

Available fields:
- region: "华北", "东北", "华南", "西北"
- basin: e.g. "松辽盆地", "滦平盆地", "准噶尔盆地", "海拉尔盆地", "天台盆地", "四川盆地", "江汉盆地", "鄂尔多斯盆地", "二连盆地", "塔里木盆地", "楚雄盆地", "渤海湾盆地", "鄱阳盆地", "柴达木盆地", "沁水盆地"
- formation: e.g. "张家口组", "龙江组", "赤城山组" etc.
- rockType: e.g. "凝灰岩", "砂岩", "花岗岩", "安山岩", "玄武岩", "泥岩", "流纹岩", "石灰岩"
- datingSystem: "U-Pb", "Ar-Ar"
- datingMineral: "锆石"
- technique: "LA-ICP-MS", "SIMS", "SHRIMP-II", "LA-MC-ICP-MS"
- age_min / age_max: numeric age in Ma
- intent: "query" | "count" | "oldest" | "youngest" | "statistics" | "none"

Output ONLY valid JSON. No markdown, no explanation.

Examples:
"华北地区有哪些样品？" → {"region":"华北","intent":"query"}
"最古老的样品是什么？" → {"intent":"oldest"}
"华南有多少个 U-Pb 锆石样品？" → {"region":"华南","datingSystem":"U-Pb","datingMineral":"锆石","intent":"count"}
"年龄大于 150 Ma 的凝灰岩" → {"rockType":"凝灰岩","age_min":150,"intent":"query"}
"松辽盆地样品年龄范围？" → {"basin":"松辽盆地","intent":"statistics"}
"东北地区最年轻的样品" → {"region":"东北","intent":"youngest"}
"今天天气怎么样" → {"intent":"none"}
"""

FORMAT_SYSTEM = """\
You are a geochronology data assistant. Given the user's original question and the matching sample data from a database,
compose a clear, concise answer in the SAME language as the user's question.

CRITICAL RULES:
- ONLY use data from the provided search results below. NEVER invent, assume, or hallucinate any data.
- Do NOT fabricate sample IDs, ages, locations, formations, rock types, or any other information.
- If the search results say "No matching samples found", respond: "未在数据库中找到相关记录" and STOP. Do not add any other information.
- If the question cannot be answered from the provided data, say: "该问题无法从数据库中查询到相关信息。"
- Keep the answer under 300 words.
- Use bullet points for lists if more than 3 samples.

Formatting rules:
- If samples were found, summarize key info (sample ID, location, age, rock type).
- For count queries, just state the number.
- For oldest/youngest, highlight that sample.
- For statistics, show age range, mean, and count.
"""


# ── RAG Pipeline ────────────────────────────────────────────────────────────

class RAGPipeline:
    def __init__(self):
        self._mimo_kwargs = dict(
            api_key=os.environ.get("MIMO_API_KEY", ""),
            base_url=os.environ.get("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1"),
            model=os.environ.get("MIMO_MODEL", "mimo-v2.5-pro"),
            cache_db=os.environ.get("MIMO_CACHE_DB", str(Path(__file__).resolve().parent / "rag_cache.sqlite")),
        )
        self.samples = SAMPLES

    def _get_client(self) -> MiMoClient:
        """Create MiMoClient per-call so the SQLite connection lives in the calling thread."""
        return MiMoClient(**self._mimo_kwargs)

    def _parse_query(self, nl_query: str) -> dict:
        """Step 1: NL → structured filter via LLM."""
        resp = self._get_client().chat(
            nl_query,
            system=QUERY_SYSTEM,
            temperature=0.1,
            max_tokens=1024,
            use_cache=True,
        )
        raw = resp.choices[0].message.content.strip()
        # Extract JSON even if wrapped in ```json ... ```
        match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"intent": "none"}

    def _filter_samples(self, filters: dict) -> list[dict]:
        """Step 2: Apply structured filters to sample data."""
        results = list(self.samples)
        for key in ("region", "basin", "formation", "rockType", "datingSystem", "datingMineral", "technique"):
            val = filters.get(key)
            if val:
                results = [s for s in results if val in str(s.get(key, ""))]

        age_min = filters.get("age_min")
        age_max = filters.get("age_max")
        if age_min is not None:
            results = [s for s in results if s.get("ageMa") is not None and s["ageMa"] >= float(age_min)]
        if age_max is not None:
            results = [s for s in results if s.get("ageMa") is not None and s["ageMa"] <= float(age_max)]

        intent = filters.get("intent", "query")
        if intent == "oldest":
            with_age = [s for s in results if s.get("ageMa") is not None]
            if with_age:
                oldest = max(with_age, key=lambda s: s["ageMa"])
                return [oldest]
            return []
        if intent == "youngest":
            with_age = [s for s in results if s.get("ageMa") is not None]
            if with_age:
                youngest = min(with_age, key=lambda s: s["ageMa"])
                return [youngest]
            return []

        return results

    def _format_answer(self, nl_query: str, samples: list[dict], intent: str) -> str:
        """Step 3: Format matching samples into natural language via LLM."""
        if intent == "count":
            return f"共找到 {len(samples)} 条符合条件的样品。"

        if not samples:
            context = "No matching samples found in the database."
        else:
            # Summarize samples for the LLM (avoid sending all fields)
            summaries = []
            for s in samples[:15]:  # Cap at 15 to control token usage
                age_str = f"{s['ageMa']} Ma ± {s['error']}" if s.get("ageMa") else "无年龄数据"
                summaries.append(
                    f"- {s['sampleId']}: {s['region']}·{s['basin']}·{s['formation']}，"
                    f"{s['rockType']}，{age_str}，{s['technique']}，ref: {s['reference']}"
                )
            if len(samples) > 15:
                summaries.append(f"... 等共 {len(samples)} 条样品")
            context = "\n".join(summaries)

        if intent == "statistics":
            ages = [s["ageMa"] for s in samples if s.get("ageMa") is not None]
            if ages:
                stats = (
                    f"Age statistics (n={len(ages)}):\n"
                    f"  Min: {min(ages)} Ma\n"
                    f"  Max: {max(ages)} Ma\n"
                    f"  Mean: {sum(ages)/len(ages):.1f} Ma"
                )
                context = stats + "\n\n" + context

        user_msg = f"Question: {nl_query}\n\nData:\n{context}"

        resp = self._get_client().chat(
            user_msg,
            system=FORMAT_SYSTEM,
            temperature=0.3,
            max_tokens=2048,
            use_cache=False,
        )
        return resp.choices[0].message.content.strip()

    def query(self, nl_query: str) -> dict:
        """Full RAG pipeline. Returns {answer, samples, filters}."""
        filters = self._parse_query(nl_query)
        intent = filters.get("intent", "query")

        # intent="none" → completely unrelated to the database, respond without LLM
        if intent == "none":
            return {
                "answer": "该问题与数据库无关。我可以帮你查询地质样品数据，例如：\n- 华北地区有哪些样品？\n- 年龄大于150 Ma的凝灰岩\n- 松辽盆地样品年龄范围？",
                "samples": [],
                "filters": filters,
            }

        matched = self._filter_samples(filters)

        # No matches → respond directly without calling LLM (prevent hallucination)
        if not matched and intent not in ("count", "statistics"):
            return {
                "answer": "未在数据库中找到符合条件的记录。",
                "samples": [],
                "filters": filters,
            }

        answer = self._format_answer(nl_query, matched, intent)
        return {
            "answer": answer,
            "samples": matched,
            "filters": filters,
        }
