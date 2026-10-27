"""
MiMo API 客户端 — 支持 SQLite 缓存、流式输出、重试
MiMo API 完全兼容 OpenAI 格式，直接用 openai SDK 调用
"""

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI
from openai.types.chat import ChatCompletion

# ── 配置 ────────────────────────────────────────────────────────────────────

MIMO_API_KEY = os.environ.get(
    "MIMO_API_KEY",
    "",
)

# Token Plan 端点（tp- 密钥专用）
MIMO_BASE_URL = os.environ.get(
    "MIMO_BASE_URL",
    "https://token-plan-cn.xiaomimimo.com/v1",
)

# 默认模型
DEFAULT_MODEL = os.environ.get("MIMO_MODEL", "mimo-v2.5-pro")

# 缓存数据库路径
CACHE_DB = os.environ.get(
    "MIMO_CACHE_DB",
    str(Path(__file__).parent / "mimo_cache.sqlite"),
)

# 缓存有效秒数（0 = 永不过期，默认 7 天）
CACHE_TTL = int(os.environ.get("MIMO_CACHE_TTL", str(7 * 86400)))


# ── 缓存层 ─────────────────────────────────────────────────────────────────

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
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_created ON cache(created_at)
    """)
    conn.commit()
    return conn


def _hash_request(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    **kwargs,
) -> str:
    """对请求参数取 SHA-256，作为缓存键。"""
    # 只取影响输出的参数，忽略 stream 等
    key_data = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # 加入额外的影响输出的参数
    for k in ("top_p", "frequency_penalty", "presence_penalty",
              "tools", "tool_choice", "stop", "response_format"):
        if k in kwargs and kwargs[k] is not None:
            key_data[k] = kwargs[k]
    raw = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(conn: sqlite3.Connection, req_hash: str, ttl: int) -> Optional[str]:
    row = conn.execute(
        "SELECT response, created_at FROM cache WHERE request_hash = ?",
        (req_hash,),
    ).fetchone()
    if row is None:
        return None
    response_json, created_at = row
    if ttl > 0 and (time.time() - created_at) > ttl:
        conn.execute("DELETE FROM cache WHERE request_hash = ?", (req_hash,))
        conn.commit()
        return None
    return response_json


def _cache_put(conn: sqlite3.Connection, req_hash: str, response_json: str, model: str):
    conn.execute(
        "INSERT OR REPLACE INTO cache (request_hash, response, model, created_at) "
        "VALUES (?, ?, ?, ?)",
        (req_hash, response_json, model, time.time()),
    )
    conn.commit()


# ── 客户端 ──────────────────────────────────────────────────────────────────

class MiMoClient:
    """
    用法:
        client = MiMoClient()
        resp = client.chat("你好")
        print(resp)

    带缓存（默认开启）:
        resp = client.chat("你好", use_cache=True)

    流式输出:
        for chunk in client.chat("你好", stream=True):
            print(chunk, end="", flush=True)
    """

    def __init__(
        self,
        api_key: str = MIMO_API_KEY,
        base_url: str = MIMO_BASE_URL,
        model: str = DEFAULT_MODEL,
        cache_db: str = CACHE_DB,
        cache_ttl: int = CACHE_TTL,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.cache_ttl = cache_ttl
        self._conn = _init_cache(cache_db)

    def chat(
        self,
        prompt: str,
        *,
        system: str = "",
        messages: Optional[list[dict]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_cache: bool = True,
        stream: bool = False,
        **kwargs,
    ):
        """
        单轮对话快捷方法。

        参数:
            prompt:      用户消息
            system:      系统提示词（为空则不添加）
            messages:    完整消息列表（提供时忽略 prompt/system）
            model:       模型名，为空则用默认
            temperature: 温度
            max_tokens:  最大输出 token
            use_cache:   是否使用缓存（仅非流式时生效）
            stream:      是否流式
        """
        model = model or self.model

        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        # 非流式 + 缓存
        if not stream and use_cache:
            req_hash = _hash_request(messages, model, temperature, max_tokens, **kwargs)
            cached = _cache_get(self._conn, req_hash, self.cache_ttl)
            if cached is not None:
                return ChatCompletion.model_validate(json.loads(cached))

        # 调用 API（带重试）
        response = self._call_api(messages, model, temperature, max_tokens, stream, **kwargs)

        if stream:
            return response  # 返回生成器

        # 写入缓存
        if use_cache:
            resp_dict = response.model_dump()
            _cache_put(self._conn, req_hash, json.dumps(resp_dict, ensure_ascii=False), model)

        return response

    def chat_multi(
        self,
        messages: list[dict],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_cache: bool = True,
        stream: bool = False,
        **kwargs,
    ):
        """多轮对话，直接传入完整 messages 列表。"""
        return self.chat(
            "",
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            stream=stream,
            **kwargs,
        )

    def _call_api(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
        max_retries: int = 3,
        **kwargs,
    ):
        """带指数退避重试的 API 调用。"""
        last_err = None
        for attempt in range(max_retries):
            try:
                return self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    **kwargs,
                )
            except Exception as e:
                last_err = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"[MiMo] 请求失败，{wait}s 后重试: {e}")
                    time.sleep(wait)
        raise last_err

    def clear_cache(self):
        """清空缓存。"""
        self._conn.execute("DELETE FROM cache")
        self._conn.commit()

    def cache_stats(self) -> dict:
        """返回缓存统计。"""
        row = self._conn.execute(
            "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM cache"
        ).fetchone()
        return {
            "entries": row[0],
            "oldest": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[1])) if row[1] else None,
            "newest": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[2])) if row[2] else None,
        }


# ── 便捷函数 ────────────────────────────────────────────────────────────────

_default_client: Optional[MiMoClient] = None


def get_client() -> MiMoClient:
    global _default_client
    if _default_client is None:
        _default_client = MiMoClient()
    return _default_client


def mimo_chat(prompt: str, **kwargs) -> str:
    """最简调用方式: mimo_chat('你好') → str"""
    resp = get_client().chat(prompt, **kwargs)
    return resp.choices[0].message.content


# ── 测试 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = MiMoClient()

    print("=" * 60)
    print("MiMo API 缓存客户端测试")
    print("=" * 60)

    # 首次调用（无缓存）
    print("\n[1] 首次调用（写入缓存）...")
    t0 = time.time()
    resp = client.chat("用一句话介绍你自己", use_cache=True)
    elapsed = time.time() - t0
    content = resp.choices[0].message.content
    print(f"    响应: {content[:100]}")
    print(f"    耗时: {elapsed:.2f}s")
    print(f"    模型: {resp.model}")

    # 二次调用（命中缓存）
    print("\n[2] 二次调用（应命中缓存）...")
    t0 = time.time()
    resp2 = client.chat("用一句话介绍你自己", use_cache=True)
    elapsed2 = time.time() - t0
    content2 = resp2.choices[0].message.content
    print(f"    响应: {content2[:100]}")
    print(f"    耗时: {elapsed2:.4f}s（应远快于首次）")
    assert content == content2, "缓存内容不一致！"
    print("    缓存一致性: ✓")

    # 流式调用
    print("\n[3] 流式调用（不走缓存）...")
    stream = client.chat("写一个 Python 的 hello world", stream=True, use_cache=False)
    print("    ", end="")
    for chunk in stream:
        if chunk.choices:
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True)
    print()

    # 缓存统计
    stats = client.cache_stats()
    print(f"\n[4] 缓存统计: {stats}")
    print("\n全部测试通过 ✓")
