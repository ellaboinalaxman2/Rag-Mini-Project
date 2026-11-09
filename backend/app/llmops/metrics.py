"""
In-process counters for query volume, engine distribution, success/failure,
cache hits, and fallback rate.

Thread-safe via threading.Lock. For Prometheus scraping, we expose a
snapshot() that the /metrics endpoint can render into Prometheus text format.
"""
import threading
from collections import defaultdict
from datetime import datetime, timezone


_lock = threading.Lock()

_state = {
    "total_queries": 0,
    "successful_queries": 0,
    "failed_queries": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "fallback_count": 0,
    "engine_usage": defaultdict(int),          # {"vector": n, "graph": n, "hybrid": n}
    "engine_success": defaultdict(int),
    "engine_failures": defaultdict(int),
    "retrieval_failures": defaultdict(int),    # {"vector": n, "graph": n}
    "intent_usage": defaultdict(int),          # {"definition": n, ...}
    "started_at": datetime.now(timezone.utc).isoformat(),
}


def record_query():
    with _lock:
        _state["total_queries"] += 1


def record_success(engine: str, intent: str):
    with _lock:
        _state["successful_queries"] += 1
        _state["engine_usage"][engine] += 1
        _state["engine_success"][engine] += 1
        _state["intent_usage"][intent] += 1


def record_failure(engine: str):
    with _lock:
        _state["failed_queries"] += 1
        _state["engine_failures"][engine] += 1


def record_cache_hit():
    with _lock:
        _state["cache_hits"] += 1


def record_cache_miss():
    with _lock:
        _state["cache_misses"] += 1


def record_fallback():
    with _lock:
        _state["fallback_count"] += 1


def record_retrieval_failure(engine: str):
    with _lock:
        _state["retrieval_failures"][engine] += 1


def snapshot() -> dict:
    with _lock:
        total = _state["total_queries"] or 1
        hits = _state["cache_hits"]
        misses = _state["cache_misses"]
        cache_total = hits + misses or 1

        return {
            "started_at": _state["started_at"],
            "total_queries": _state["total_queries"],
            "successful_queries": _state["successful_queries"],
            "failed_queries": _state["failed_queries"],
            "success_rate": round(
                _state["successful_queries"] / total, 4
            ),
            "cache": {
                "hits": hits,
                "misses": misses,
                "hit_ratio": round(hits / cache_total, 4),
            },
            "fallback_count": _state["fallback_count"],
            "engine_usage": dict(_state["engine_usage"]),
            "engine_success": dict(_state["engine_success"]),
            "engine_failures": dict(_state["engine_failures"]),
            "retrieval_failures": dict(_state["retrieval_failures"]),
            "intent_usage": dict(_state["intent_usage"]),
        }


def reset():
    """Test helper."""
    with _lock:
        _state["total_queries"] = 0
        _state["successful_queries"] = 0
        _state["failed_queries"] = 0
        _state["cache_hits"] = 0
        _state["cache_misses"] = 0
        _state["fallback_count"] = 0
        _state["engine_usage"].clear()
        _state["engine_success"].clear()
        _state["engine_failures"].clear()
        _state["retrieval_failures"].clear()
        _state["intent_usage"].clear()