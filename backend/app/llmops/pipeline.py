"""
Wrap the Phase 7 router with LLMOps observability + caching.
This is the recommended entry point for production-facing queries.
"""
import time

from app.router.pipeline import route_query
from app.llmops import metrics
from app.llmops import cache
from app.llmops.latency_tracker import stage_timer, record_sample
from app.llmops.logger import log_query


def observed_query(
    query: str,
    document_id: str | None = None,
    force_engine: str | None = None,
    use_cache: bool = True,
) -> dict:
    metrics.record_query()
    started = time.perf_counter()

    # --- Cache lookup (before routing, since routing metadata is deterministic) ---
    cache_key_engine = force_engine or "auto"
    cache_hit = False

    if use_cache and cache.is_enabled():
        cached = cache.get(cache_key_engine, query, document_id)
        if cached is not None:
            cache_hit = True
            metrics.record_cache_hit()
            total_ms = (time.perf_counter() - started) * 1000.0
            log_query(
                query=query,
                engine=cached.get("engine_used", "unknown"),
                intent=cached.get("routing", {}).get("intent", "unknown"),
                confidence=cached.get("routing", {}).get(
                    "routing_confidence", 0.0
                ),
                latency_ms=total_ms,
                success=True,
                cache_hit=True,
            )
            return {
                **cached,
                "cache_hit": True,
                "total_latency_ms": round(total_ms, 2),
            }
        metrics.record_cache_miss()

    # --- Real routing ---
    try:
        with stage_timer("route_and_retrieve"):
            result = route_query(
                query=query,
                document_id=document_id,
                force_engine=force_engine,
            )
    except Exception as exc:
        metrics.record_failure(force_engine or "auto")
        total_ms = (time.perf_counter() - started) * 1000.0
        log_query(
            query=query,
            engine=force_engine or "auto",
            intent="unknown",
            confidence=0.0,
            latency_ms=total_ms,
            success=False,
            error=str(exc),
        )
        raise

    # --- Track metrics ---
    engine_used = result.get("engine_used", "unknown")
    intent = result.get("routing", {}).get("intent", "unknown")
    confidence = result.get("routing", {}).get("routing_confidence", 0.0)
    fallback = result.get("routing", {}).get("fallback_applied", False)

    metrics.record_success(engine_used, intent)
    if fallback:
        metrics.record_fallback()

    # --- Token + cost tracking (from engine response if present) ---
    usage = result.get("usage") or {}
    if usage:
        from app.llmops.token_tracker import record_tokens
        from app.llmops.cost_tracker import record_cost

        model = result.get("model") or "unknown"
        pt = usage.get("prompt_tokens", 0)
        ct = usage.get("completion_tokens", 0)
        tt = usage.get("total_tokens", 0)
        record_tokens("groq", model, pt, ct, tt)
        record_cost(model, pt, ct)

    total_ms = (time.perf_counter() - started) * 1000.0
    record_sample("total_query", total_ms, engine=engine_used)

    result["cache_hit"] = False
    result["total_latency_ms"] = round(total_ms, 2)

    log_query(
        query=query,
        engine=engine_used,
        intent=intent,
        confidence=confidence,
        latency_ms=total_ms,
        success=True,
        cache_hit=False,
        fallback=fallback,
    )

    # --- Store in cache (only on success with non-empty answer) ---
    if use_cache and cache.is_enabled() and result.get("answer"):
        # Store without the transient latency/cache fields
        to_cache = {k: v for k, v in result.items() if k not in (
            "cache_hit", "total_latency_ms"
        )}
        cache.set(cache_key_engine, query, to_cache, document_id=document_id)

    return result