"""
Gemini API 客户端 — SQLite 缓存，REST 直调
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

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")

CACHE_DB = os.environ.get(
    "GEMINI_CACHE_DB",
    str(Path(__file__).parent / "gemini_cache.sqlite"),
)

CACHE_TTL = int(os.environ.get("GEMINI_CACHE_TTL", str(7 * 86400)))

API_BASE = "https://generativelanguage.googleapis.com/v1beta"


# ── 缓存 ────────────────────────────────────────────────────────────────────

def _init_cache(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            request_hash TEXT PRIMARY KEY,
            response     TEXT NOT NULL,
            model        TEXT,
            created_at   REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def _hash_request(contents: list, model: str, generation_config: dict) -> str:
    raw = json.dumps(
        {"contents": contents, "model": model, "generation_config": generation_config},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(conn: sqlite3.Connection, req_hash: str, ttl: int) -> Optional[str]:
    row = conn.execute(
        "SELECT response, created_at FROM cache WHERE request_hash = ?", (req_hash,)
    ).fetchone()
    if row is None:
        return None
    resp, created_at = row
    if ttl > 0 and (time.time() - created_at) > ttl:
        conn.execute("DELETE FROM cache WHERE request_hash = ?", (req_hash,))
        conn.commit()
        return None
    return resp


def _cache_put(conn: sqlite3.Connection, req_hash: str, response: str, model: str):
    conn.execute(
        "INSERT OR REPLACE INTO cache (request_hash, response, model, created_at) "
        "VALUES (?, ?, ?, ?)",
        (req_hash, response, model, time.time()),
    )
    conn.commit()


# ── 客户端 ──────────────────────────────────────────────────────────────────

class GeminiClient:
    def __init__(
        self,
        api_key: str = GEMINI_API_KEY,
        model: str = DEFAULT_MODEL,
        cache_db: str = CACHE_DB,
        cache_ttl: int = CACHE_TTL,
    ):
        self.api_key = api_key
        self.model = model
        self.cache_ttl = cache_ttl
        self._conn = _init_cache(cache_db)

    def chat(
        self,
        prompt: str,
        *,
        system: str = "",
        contents: Optional[list] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_cache: bool = True,
    ) -> str:
        model = model or self.model

        if contents is None:
            contents = []
            if system:
                contents.append({"role": "user", "parts": [{"text": system}]})
                contents.append({"role": "model", "parts": [{"text": "好的，我明白了。"}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})

        generation_config = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }

        if use_cache:
            req_hash = _hash_request(contents, model, generation_config)
            cached = _cache_get(self._conn, req_hash, self.cache_ttl)
            if cached is not None:
                return cached

        response_text = self._call_api(contents, model, generation_config)

        if use_cache:
            _cache_put(self._conn, req_hash, response_text, model)

        return response_text

    def chat_multi(self, messages: list[dict], **kwargs) -> str:
        """多轮对话，messages 格式: [{"role": "user"/"model", "content": "..."}]"""
        contents = [
            {"role": m["role"], "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        return self.chat("", contents=contents, **kwargs)

    def _call_api(
        self,
        contents: list,
        model: str,
        generation_config: dict,
        max_retries: int = 3,
    ) -> str:
        url = f"{API_BASE}/models/{model}:generateContent?key={self.api_key}"
        payload = json.dumps({
            "contents": contents,
            "generationConfig": generation_config,
        }).encode()

        last_err = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url, data=payload, headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read())
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                last_err = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"[Gemini] 请求失败，{wait}s 后重试: {e}")
                    time.sleep(wait)
        raise last_err

    def clear_cache(self):
        self._conn.execute("DELETE FROM cache")
        self._conn.commit()

    def cache_stats(self) -> dict:
        row = self._conn.execute(
            "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM cache"
        ).fetchone()
        return {
            "entries": row[0],
            "oldest": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[1])) if row[1] else None,
            "newest": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[2])) if row[2] else None,
        }


# ── 测试 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = GeminiClient()

    print("=" * 60)
    print("Gemini flash-lite 缓存客户端测试")
    print("=" * 60)

    # 首次
    print("\n[1] 首次调用（写入缓存）...")
    t0 = time.time()
    resp = client.chat("你好，用一句话介绍你自己")
    print(f"    响应: {resp[:80]}")
    print(f"    耗时: {time.time() - t0:.2f}s")

    # 二次（命中缓存）
    print("\n[2] 二次调用（应命中缓存）...")
    t0 = time.time()
    resp2 = client.chat("你好，用一句话介绍你自己")
    print(f"    响应: {resp2[:80]}")
    print(f"    耗时: {time.time() - t0:.4f}s")
    assert resp == resp2, "缓存内容不一致！"
    print("    缓存一致性: ✓")

    # 不同 prompt（新请求）
    print("\n[3] 不同 prompt（不走缓存）...")
    t0 = time.time()
    resp3 = client.chat("1+1等于几？只回答数字")
    print(f"    响应: {resp3.strip()}")
    print(f"    耗时: {time.time() - t0:.2f}s")

    stats = client.cache_stats()
    print(f"\n[4] 缓存统计: {stats}")
    print("\n全部测试通过 ✓")
