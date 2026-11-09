"""
Estimated API cost based on configured per-model pricing.
Never treat these as actual billed amounts — they're estimates for monitoring.
"""
import os
import threading
from collections import defaultdict


_lock = threading.Lock()

# model_name → {input_cost_usd, output_cost_usd, calls}
_totals: dict[str, dict] = defaultdict(
    lambda: {"input_cost_usd": 0.0, "output_cost_usd": 0.0, "calls": 0}
)


def _rate(model: str, kind: str) -> float:
    """Resolve $/1M-token rate from env, with sensible fallbacks."""
    model_l = model.lower()

    if "groq" in model_l or "llama" in model_l or "mixtral" in model_l:
        env_key = (
            "GROQ_INPUT_COST_PER_1M"
            if kind == "input"
            else "GROQ_OUTPUT_COST_PER_1M"
        )
        default = 0.59 if kind == "input" else 0.79
    elif "gemini" in model_l:
        env_key = (
            "GEMINI_INPUT_COST_PER_1M"
            if kind == "input"
            else "GEMINI_OUTPUT_COST_PER_1M"
        )
        default = 0.075 if kind == "input" else 0.30
    else:
        env_key = (
            "GROQ_INPUT_COST_PER_1M"
            if kind == "input"
            else "GROQ_OUTPUT_COST_PER_1M"
        )
        default = 0.59 if kind == "input" else 0.79

    try:
        return float(os.getenv(env_key, default))
    except (TypeError, ValueError):
        return default


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> dict:
    input_rate = _rate(model, "input")
    output_rate = _rate(model, "output")

    input_cost = (prompt_tokens * input_rate) / 1_000_000.0
    output_cost = (completion_tokens * output_rate) / 1_000_000.0
    total = input_cost + output_cost

    return {
        "input_cost_usd": round(input_cost, 8),
        "output_cost_usd": round(output_cost, 8),
        "total_cost_usd": round(total, 8),
        "input_rate_per_1m": input_rate,
        "output_rate_per_1m": output_rate,
    }


def record_cost(model: str, prompt_tokens: int, completion_tokens: int):
    cost = calculate_cost(model, prompt_tokens, completion_tokens)
    with _lock:
        bucket = _totals[model]
        bucket["input_cost_usd"] += cost["input_cost_usd"]
        bucket["output_cost_usd"] += cost["output_cost_usd"]
        bucket["calls"] += 1
    return cost


def snapshot() -> dict:
    with _lock:
        return {
            model: {
                "input_cost_usd": round(b["input_cost_usd"], 6),
                "output_cost_usd": round(b["output_cost_usd"], 6),
                "total_cost_usd": round(
                    b["input_cost_usd"] + b["output_cost_usd"], 6
                ),
                "calls": b["calls"],
            }
            for model, b in _totals.items()
        }


def grand_total() -> dict:
    with _lock:
        in_cost = sum(b["input_cost_usd"] for b in _totals.values())
        out_cost = sum(b["output_cost_usd"] for b in _totals.values())
        calls = sum(b["calls"] for b in _totals.values())
        return {
            "input_cost_usd": round(in_cost, 6),
            "output_cost_usd": round(out_cost, 6),
            "total_cost_usd": round(in_cost + out_cost, 6),
            "calls": calls,
        }


def reset():
    with _lock:
        _totals.clear()