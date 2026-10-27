"""
RAG pipeline v3: Uses real 437-sample data from sample_loader.
Same NL→filter→search→answer pattern as rag.py but with actual pipeline output.
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from mimo_client import MiMoClient

from sample_loader import load_samples, load_papers

QUERY_SYSTEM = """\
You are a database query parser for a geological sample database containing 437 geochronology samples from southeastern China (华南).

Convert the user's question into a JSON filter object to search this database.

CRITICAL RULES:
- You are ONLY a query parser. You do NOT answer questions yourself.
- When the user asks about "samples" (样品/标本), "data" (数据), asks "which/what" (有哪些/是什么),
  or mentions ANY region/basin/formation/rock type/age — it is ALWAYS a database query (intent="query").
- If the question asks about geological concepts, stratigraphy, or sample analysis that COULD relate to the database,
  use intent="query" with an empty filter to return all samples.
- ONLY use intent="none" for completely unrelated questions (e.g. "what's the weather?", "tell me a joke").

Available fields:
- region: "华南" (all 437 samples are from 华南/southeastern China)
- basin: e.g. "天台盆地"/"Tiantai Basin", "建德盆地", "永安盆地"/"Yong'an Basin", "丽水盆地", "信江盆地", "永康盆地"/"Yongkang Basin", "泰宁盆地", "沙县盆地", "金衢盆地", "二连盆地", "上杭盆地"
- formation: e.g. "馆头组", "西山头组", "茶湾组", "沙县组", "劳村组", "坂头组", "朝川组", "寨下组", "黄尖组", "打鼓顶组", "高坞组", "九里坪组"
- rockType: e.g. "凝灰岩", "tuff", "粗面岩", "橄榄玄武岩", "熔结凝灰岩", "玄武安山岩", "流纹岩", "英安岩"
- datingSystem: "U-Th-Pb dating", "Ar-Ar dating", "K-Ar dating", "Rb-Sr dating"
- datingMineral: "Zircon", "Matrix", "Whole rock", "K-feldspar", "Sanidine"
- technique: "LA-ICPMS", "SHRIMP", "CAMECA SIMS", "Other"
- age_min / age_max: numeric age in Ma
- intent: "query" | "count" | "oldest" | "youngest" | "statistics" | "none"

Output ONLY valid JSON. No markdown, no explanation.

Examples:
"浙江有哪些凝灰岩样品？" → {"basin":"建德盆地","rockType":"凝灰岩","intent":"query"}
"最古老的样品是什么？" → {"intent":"oldest"}
"有多少个 U-Pb 锆石样品？" → {"datingSystem":"U-Th-Pb dating","datingMineral":"Zircon","intent":"count"}
"年龄大于 100 Ma 的样品" → {"age_min":100,"intent":"query"}
"馆头组的玄武岩" → {"formation":"馆头组","rockType":"玄武岩","intent":"query"}
"有多少 Ar-Ar 定年样品" → {"datingSystem":"Ar-Ar dating","intent":"count"}
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


class RAGPipelineV3:
    def __init__(self):
        self._mimo_kwargs = dict(
            api_key=os.environ.get("MIMO_API_KEY", ""),
            base_url=os.environ.get("MIMO_BASE_URL", "https://token-plan-cn.xiaomimomo.com/v1"),
            model=os.environ.get("MIMO_MODEL", "mimo-v2.5-pro"),
            cache_db=os.environ.get("MIMO_CACHE_DB", str(Path(__file__).resolve().parent / "rag_cache.sqlite")),
        )
        self.samples = load_samples()
        self.papers = load_papers()

    def reload(self):
        """Reload samples from pipeline output."""
        self.samples = load_samples()
        self.papers = load_papers()
        return len(self.samples)

    def _get_client(self) -> MiMoClient:
        return MiMoClient(**self._mimo_kwargs)

    def _parse_query(self, nl_query: str) -> dict:
        resp = self._get_client().chat(
            nl_query,
            system=QUERY_SYSTEM,
            temperature=0.1,
            max_tokens=1024,
            use_cache=True,
        )
        raw = resp.choices[0].message.content.strip()
        match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"intent": "none"}

    def _filter_samples(self, filters: dict) -> list[dict]:
        results = list(self.samples)
        for key in ("region", "basin", "formation", "rockType", "datingSystem", "datingMineral", "technique"):
            val = filters.get(key)
            if val:
                results = [s for s in results if val.lower() in str(s.get(key, "")).lower()]

        age_min = filters.get("age_min")
        age_max = filters.get("age_max")
        if age_min is not None:
            results = [s for s in results if s.get("ageMa") is not None and s["ageMa"] >= float(age_min)]
        if age_max is not None:
            results = [s for s in results if s.get("ageMa") is not None and s["ageMa"] <= float(age_max)]

        intent = filters.get("intent", "query")
        if intent == "oldest":
            with_age = [s for s in results if s.get("ageMa") is not None]
            return [max(with_age, key=lambda s: s["ageMa"])] if with_age else []
        if intent == "youngest":
            with_age = [s for s in results if s.get("ageMa") is not None]
            return [min(with_age, key=lambda s: s["ageMa"])] if with_age else []

        return results

    def _format_answer(self, nl_query: str, samples: list[dict], intent: str) -> str:
        if intent == "count":
            return f"共找到 {len(samples)} 条符合条件的样品。"

        if not samples:
            return "未在数据库中找到符合条件的记录。"

        summaries = []
        for s in samples[:15]:
            age_str = f"{s['ageMa']} Ma ± {s['error']}" if s.get("ageMa") else "无年龄数据"
            summaries.append(
                f"- {s['sampleId']}: {s.get('regionProvince','')}·{s.get('basin','')}·{s.get('formation','')}，"
                f"{s.get('rockType','')}，{age_str}，{s.get('technique','')}，ref: {s.get('reference','')}"
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
        filters = self._parse_query(nl_query)
        intent = filters.get("intent", "query")

        if intent == "none":
            return {
                "answer": "该问题与数据库无关。我可以帮你查询地质样品数据，例如：\n- 有哪些凝灰岩样品？\n- 年龄大于100 Ma的样品\n- 馆头组的玄武岩\n- 最古老的样品是什么？",
                "samples": [],
                "filters": filters,
            }

        matched = self._filter_samples(filters)

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
