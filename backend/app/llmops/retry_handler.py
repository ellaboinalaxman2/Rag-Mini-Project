"""
Retry with exponential backoff for LLM provider calls.
Handles rate limits, timeouts, and transient errors.
"""
import os
import time


class RetryExhausted(RuntimeError):
    pass


def _max_retries() -> int:
    try:
        return int(os.getenv("LLM_MAX_RETRIES", "3"))
    except ValueError:
        return 3


def _base_delay() -> float:
    try:
        return float(os.getenv("LLM_RETRY_BASE_DELAY", "0.5"))
    except ValueError:
        return 0.5


def _is_retryable(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()

    # Don't retry auth / config errors
    for token in ("auth", "api key", "api_key", "not configured", "invalid_request"):
        if token in msg:
            return False

    # Retry on rate limit, timeout, connection, server errors
    for token in ("rate", "429", "timeout", "timed out", "connection",
                  "502", "503", "504", "temporar", "overload"):
        if token in msg or token in name:
            return True

    # Unknown → don't retry by default (safer)
    return False


def with_retry(func, *args, **kwargs):
    attempts = _max_retries()
    base = _base_delay()
    last_exc: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts or not _is_retryable(exc):
                raise
            delay = base * (2 ** (attempt - 1))
            print(
                f"[retry] attempt {attempt}/{attempts} failed: {exc}; "
                f"sleeping {delay:.2f}s"
            )
            time.sleep(delay)

    raise RetryExhausted(f"All {attempts} retries failed: {last_exc}")