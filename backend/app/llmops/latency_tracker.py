"""
Per-stage latency tracking with a context-manager API.
"""
import threading
import time
from collections import defaultdict
from contextlib import contextmanager


_lock = threading.Lock()

# engine → stage → list of ms samples (capped at 1000 to bound memory)
_samples: dict[str, dict[str, list[float]]] = defaultdict(
    lambda: defaultdict(list)
)

MAX_SAMPLES = 1000


def _cap(lst: list):
    if len(lst) > MAX_SAMPLES:
        del lst[: len(lst) - MAX_SAMPLES]


@contextmanager
def stage_timer(stage: str, engine: str = "any"):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        with _lock:
            bucket = _samples[engine][stage]
            bucket.append(round(elapsed_ms, 2))
            _cap(bucket)


def record_sample(stage: str, ms: float, engine: str = "any"):
    with _lock:
        bucket = _samples[engine][stage]
        bucket.append(round(ms, 2))
        _cap(bucket)


def _stats(lst: list) -> dict:
    if not lst:
        return {"count": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0, "p95_ms": 0}

    sorted_lst = sorted(lst)
    p95_idx = max(0, int(len(sorted_lst) * 0.95) - 1)
    return {
        "count": len(lst),
        "avg_ms": round(sum(lst) / len(lst), 2),
        "min_ms": round(min(lst), 2),
        "max_ms": round(max(lst), 2),
        "p95_ms": round(sorted_lst[p95_idx], 2),
    }


def snapshot() -> dict:
    with _lock:
        out = {}
        for engine, stages in _samples.items():
            out[engine] = {stage: _stats(list(samples)) for stage, samples in stages.items()}
        return out


def reset():
    with _lock:
        _samples.clear()