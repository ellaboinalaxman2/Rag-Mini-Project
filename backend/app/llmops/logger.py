"""
Structured-ish logging helper. Emits JSON-like lines for easy grep.
"""
import json
import logging
import sys
from datetime import datetime, timezone


_logger = logging.getLogger("rag_llmops")
_logger.setLevel(logging.INFO)

if not _logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(message)s")
    handler.setFormatter(fmt)
    _logger.addHandler(handler)
    _logger.propagate = False


def log_event(event: str, **fields):
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    try:
        _logger.info(json.dumps(payload, default=str))
    except Exception:
        _logger.info(f"{event} | {fields}")


def log_query(
    query: str,
    engine: str,
    intent: str,
    confidence: float,
    latency_ms: float,
    success: bool,
    cache_hit: bool = False,
    fallback: bool = False,
    error: str | None = None,
):
    log_event(
        "query",
        query=query[:200],
        engine=engine,
        intent=intent,
        confidence=confidence,
        latency_ms=round(latency_ms, 2),
        success=success,
        cache_hit=cache_hit,
        fallback=fallback,
        error=error,
    )