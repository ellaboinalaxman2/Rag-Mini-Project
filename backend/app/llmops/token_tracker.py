"""
Track LLM token consumption per provider/model.
"""
import threading
from collections import defaultdict


_lock = threading.Lock()

# provider → model → {prompt, completion, total, calls}
_totals: dict[str, dict[str, dict]] = defaultdict(
    lambda: defaultdict(
        lambda: {"prompt": 0, "completion": 0, "total": 0, "calls": 0}
    )
)


def record_tokens(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int | None = None,
):
    if total_tokens is None:
        total_tokens = prompt_tokens + completion_tokens

    with _lock:
        bucket = _totals[provider][model]
        bucket["prompt"] += int(prompt_tokens or 0)
        bucket["completion"] += int(completion_tokens or 0)
        bucket["total"] += int(total_tokens or 0)
        bucket["calls"] += 1


def snapshot() -> dict:
    with _lock:
        return {
            provider: {
                model: dict(stats) for model, stats in models.items()
            }
            for provider, models in _totals.items()
        }


def grand_total() -> dict:
    with _lock:
        prompt = completion = total = calls = 0
        for models in _totals.values():
            for stats in models.values():
                prompt += stats["prompt"]
                completion += stats["completion"]
                total += stats["total"]
                calls += stats["calls"]
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "llm_calls": calls,
        }


def reset():
    with _lock:
        _totals.clear()