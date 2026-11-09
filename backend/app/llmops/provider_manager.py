"""
Wrap LLM calls with retry + token/cost tracking.
Primary provider = Groq (from .env GROQ_MODEL).
Gemini fallback wired in Phase 8B when Gemini client is added to the project.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from app.llmops.retry_handler import with_retry
from app.llmops.token_tracker import record_tokens
from app.llmops.cost_tracker import record_cost
from app.llmops.logger import log_event

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


def _groq_call(messages, temperature, max_tokens=None):
    api_key = os.getenv("GROQ_API_KEY")
    model_name = os.getenv("GROQ_MODEL")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    if not model_name:
        raise RuntimeError("GROQ_MODEL is not configured.")

    client = Groq(api_key=api_key)
    kwargs = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    return client.chat.completions.create(**kwargs)


def call_llm(
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int | None = None,
):
    """
    Returns:
        {
            "content": str,
            "model": str,
            "provider": "groq",
            "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
            "cost_usd": float,
        }
    """
    response = with_retry(
        _groq_call, messages, temperature, max_tokens
    )

    model_name = getattr(response, "model", None) or os.getenv(
        "GROQ_MODEL", "unknown"
    )

    usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    if response.usage:
        usage["prompt_tokens"] = response.usage.prompt_tokens or 0
        usage["completion_tokens"] = response.usage.completion_tokens or 0
        usage["total_tokens"] = response.usage.total_tokens or 0

    # Track tokens + cost
    record_tokens(
        provider="groq",
        model=model_name,
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        total_tokens=usage["total_tokens"],
    )
    cost = record_cost(
        model=model_name,
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
    )

    content = response.choices[0].message.content if response.choices else ""

    log_event(
        "llm_call",
        provider="groq",
        model=model_name,
        tokens=usage,
        cost_usd=cost["total_cost_usd"],
    )

    return {
        "content": content,
        "model": model_name,
        "provider": "groq",
        "usage": usage,
        "cost_usd": cost["total_cost_usd"],
    }


def provider_status() -> dict:
    return {
        "groq": {
            "configured": bool(os.getenv("GROQ_API_KEY")),
            "model": os.getenv("GROQ_MODEL"),
            "status": (
                "ready" if os.getenv("GROQ_API_KEY") else "not_configured"
            ),
        },
        "gemini": {
            "configured": bool(os.getenv("GEMINI_API_KEY")),
            "model": os.getenv("GEMINI_MODEL"),
            "status": (
                "configured_not_wired"
                if os.getenv("GEMINI_API_KEY")
                else "not_configured"
            ),
        },
    }