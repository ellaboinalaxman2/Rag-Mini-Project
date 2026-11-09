"""
Redis cache for RAG query results.
Key = sha256(prefix + engine + normalized_query + document_id + version)
Fails open — if Redis is down, we just skip caching and log a warning.
"""
import hashlib
import json
import os
from pathlib import Path

import redis
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")

CACHE_VERSION = "v1"

_client = None
_disabled = False


def _get_client():
    global _client, _disabled
    if _disabled:
        return None

    if _client is not None:
        return _client

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
        _client = client
        return _client
    except Exception as exc:
        print(f"[cache] Redis unavailable, caching disabled: {exc}")
        _disabled = True
        return None


def is_enabled() -> bool:
    if os.getenv("CACHE_ENABLED", "true").lower() in ("false", "0", "no"):
        return False
    return _get_client() is not None


def _make_key(engine: str, query: str, document_id: str | None) -> str:
    prefix = os.getenv("CACHE_PREFIX", "rag:cache:")
    normalized = " ".join(query.strip().lower().split())
    doc = document_id or "none"
    identity = f"{CACHE_VERSION}|{engine}|{normalized}|{doc}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"{prefix}{digest}"


def get(engine: str, query: str, document_id: str | None = None):
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(_make_key(engine, query, document_id))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        print(f"[cache] get failed: {exc}")
        return None


def set(
    engine: str,
    query: str,
    result: dict,
    document_id: str | None = None,
    ttl_seconds: int | None = None,
):
    client = _get_client()
    if client is None:
        return False
    try:
        ttl = ttl_seconds
        if ttl is None:
            try:
                ttl = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
            except ValueError:
                ttl = 3600
        payload = json.dumps(result)
        client.setex(
            _make_key(engine, query, document_id),
            ttl,
            payload,
        )
        return True
    except Exception as exc:
        print(f"[cache] set failed: {exc}")
        return False


def invalidate_document(document_id: str):
    """
    Best-effort: delete all cache keys whose payload mentions this document_id.
    Since we don't index by document_id, this is a scan-and-delete.
    Fine for small local deployments; for production use a Redis set of keys per doc.
    """
    client = _get_client()
    if client is None:
        return 0
    try:
        prefix = os.getenv("CACHE_PREFIX", "rag:cache:")
        count = 0
        for key in client.scan_iter(match=f"{prefix}*", count=500):
            try:
                raw = client.get(key)
                if raw and document_id in raw:
                    client.delete(key)
                    count += 1
            except Exception:
                continue
        return count
    except Exception as exc:
        print(f"[cache] invalidate failed: {exc}")
        return 0


def flush():
    client = _get_client()
    if client is None:
        return False
    try:
        prefix = os.getenv("CACHE_PREFIX", "rag:cache:")
        for key in client.scan_iter(match=f"{prefix}*", count=500):
            client.delete(key)
        return True
    except Exception as exc:
        print(f"[cache] flush failed: {exc}")
        return False