from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.llmops import metrics
from app.llmops import latency_tracker
from app.llmops import token_tracker
from app.llmops import cost_tracker
from app.llmops import cache
from app.llmops.provider_manager import provider_status

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


@router.get("/health")
def monitoring_health():
    return {
        "success": True,
        "service": "monitoring",
        "cache_enabled": cache.is_enabled(),
    }


@router.get("/metrics")
def app_metrics():
    return {
        "success": True,
        "metrics": metrics.snapshot(),
        "latency": latency_tracker.snapshot(),
    }


@router.get("/summary")
def performance_summary():
    return {
        "success": True,
        "summary": {
            "queries": metrics.snapshot(),
            "tokens": token_tracker.grand_total(),
            "cost": cost_tracker.grand_total(),
            "cache_enabled": cache.is_enabled(),
        },
    }


@router.get("/costs")
def costs():
    return {
        "success": True,
        "by_model": cost_tracker.snapshot(),
        "total": cost_tracker.grand_total(),
    }


@router.get("/tokens")
def tokens():
    return {
        "success": True,
        "by_provider_model": token_tracker.snapshot(),
        "total": token_tracker.grand_total(),
    }


@router.get("/providers")
def providers():
    return {
        "success": True,
        "providers": provider_status(),
    }


@router.post("/cache/flush")
def cache_flush():
    ok = cache.flush()
    if not ok:
        raise HTTPException(
            status_code=503,
            detail="Cache unavailable or flush failed.",
        )
    return {"success": True, "message": "Cache flushed"}


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
def prometheus_metrics():
    """
    Minimal Prometheus-format output. Phase 8B will swap this for the
    official prometheus_client registry; for now we expose raw counters.
    """
    snap = metrics.snapshot()
    total = token_tracker.grand_total()
    cost = cost_tracker.grand_total()

    lines = [
        "# HELP rag_total_queries Total queries handled",
        "# TYPE rag_total_queries counter",
        f"rag_total_queries {snap['total_queries']}",
        "# HELP rag_successful_queries Successful queries",
        "# TYPE rag_successful_queries counter",
        f"rag_successful_queries {snap['successful_queries']}",
        "# HELP rag_failed_queries Failed queries",
        "# TYPE rag_failed_queries counter",
        f"rag_failed_queries {snap['failed_queries']}",
        "# HELP rag_cache_hits Total cache hits",
        "# TYPE rag_cache_hits counter",
        f"rag_cache_hits {snap['cache']['hits']}",
        "# HELP rag_cache_misses Total cache misses",
        "# TYPE rag_cache_misses counter",
        f"rag_cache_misses {snap['cache']['misses']}",
        "# HELP rag_fallback_count Total fallbacks",
        "# TYPE rag_fallback_count counter",
        f"rag_fallback_count {snap['fallback_count']}",
        "# HELP rag_total_tokens Total tokens consumed",
        "# TYPE rag_total_tokens counter",
        f"rag_total_tokens {total['total_tokens']}",
        "# HELP rag_estimated_cost_usd Estimated total cost in USD",
        "# TYPE rag_estimated_cost_usd gauge",
        f"rag_estimated_cost_usd {cost['total_cost_usd']}",
    ]

    for engine, count in snap["engine_usage"].items():
        lines.append(
            f'rag_engine_usage_total{{engine="{engine}"}} {count}'
        )

    return "\n".join(lines) + "\n"