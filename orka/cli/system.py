# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
System CLI Commands
===================

`orka system status` — a real reachability/health check for the local stack:
Redis connectivity, RediSearch (vector index) availability, and the configured
local LLM endpoint. Replaces the previously documented-but-nonexistent command.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


def _sanitize_url(url: str) -> str:
    """Strip credentials from a URL so health output never leaks secrets."""
    try:
        parsed = urlparse(url)
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        return "<redacted>"


def _check_redis(redis_url: str) -> dict[str, Any]:
    """Synchronous Redis + RediSearch reachability probe."""
    out: dict[str, Any] = {
        "url": _sanitize_url(redis_url),
        "connected": False,
        "ping_ms": None,
        "search_module": False,
        "indexes": None,
        "error": None,
    }
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=3)
        t0 = time.perf_counter()
        out["connected"] = bool(client.ping())
        out["ping_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        try:
            indexes = client.execute_command("FT._LIST")
            out["search_module"] = True
            out["indexes"] = [
                i.decode("utf-8") if isinstance(i, bytes) else i for i in indexes
            ]
        except Exception:
            # RediSearch module not loaded (plain Redis) — vector search unavailable.
            out["search_module"] = False
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def _check_llm() -> dict[str, Any]:
    """Best-effort probe of the configured local LLM endpoint (OpenAI-compatible)."""
    url = os.getenv("ORKA_LLM_URL", "http://localhost:1234")
    out: dict[str, Any] = {"url": url, "reachable": False, "models": None, "error": None}
    try:
        import httpx

        resp = httpx.get(f"{url.rstrip('/')}/v1/models", timeout=3.0)
        if resp.status_code == 200:
            out["reachable"] = True
            data = resp.json()
            out["models"] = [m.get("id") for m in data.get("data", [])][:10]
        else:
            out["error"] = f"HTTP {resp.status_code}"
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def _orka_version() -> str:
    try:
        from importlib.metadata import version

        return version("orka-reasoning")
    except Exception:
        return "unknown"


def system_status(args: Any) -> int:
    """Report OrKa version and reachability of Redis, RediSearch, and the local LLM."""
    backend = getattr(args, "backend", None) or os.getenv("ORKA_MEMORY_BACKEND", "redisstack")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")

    redis_info = _check_redis(redis_url)
    llm_info = _check_llm()
    report = {
        "version": _orka_version(),
        "backend": backend,
        "redis": redis_info,
        "llm": llm_info,
    }

    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
    else:
        ok = "[OK]"
        bad = "[FAIL]"
        print("=== OrKa System Status ===")
        print(f"Version: {report['version']}")
        print(f"Backend: {backend}")
        r = redis_info
        rstate = ok if r["connected"] else bad
        print(f"{rstate} Redis: {r['url']}" + (f" ({r['ping_ms']}ms)" if r["connected"] else f" — {r['error']}"))
        if r["connected"]:
            sstate = ok if r["search_module"] else "[WARN]"
            idx = f"{len(r['indexes'])} index(es)" if r["indexes"] is not None else "n/a"
            print(
                f"{sstate} RediSearch: "
                + ("available, " + idx if r["search_module"] else "NOT loaded — vector search degraded to scan")
            )
        l = llm_info
        lstate = ok if l["reachable"] else "[WARN]"
        if l["reachable"]:
            models = ", ".join(l["models"] or []) or "none listed"
            print(f"{lstate} LLM endpoint: {l['url']} — {models}")
        else:
            print(f"{lstate} LLM endpoint: {l['url']} — unreachable ({l['error']})")

    # Exit non-zero only when the core dependency (Redis) is down.
    return 0 if redis_info["connected"] else 1
