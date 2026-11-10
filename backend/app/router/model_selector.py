"""
Selects the appropriate AI model for general fallback questions based on
the burden (complexity, depth, reasoning intensity) of the user's question.
"""
import os
import re


def assess_question_burden(query: str, complexity_info: dict | None = None) -> dict:
    """
    Assess the burden (difficulty/complexity/strongness) of a question and
    select the most cost-effective and capable AI model.

    Returns:
        {
            "burden": "high" | "medium" | "low",
            "model": str,
            "reason": str,
            "signals": list[str],
        }
    """
    q_lower = query.lower()
    words = len(re.findall(r"\w+", query))

    # Heavy burden indicators (deep reasoning, technical synthesis, comparison, code)
    heavy_signals = [
        "why", "how come", "explain in detail", "step by step",
        "compare", "difference between", "pros and cons", "versus", "vs",
        "code", "algorithm", "implement", "debug", "write a", "architecture",
        "calculate", "derive", "proof", "evaluate", "analyze", "deep dive"
    ]
    heavy_hits = [s for s in heavy_signals if s in q_lower]

    # Medium burden indicators (conceptual explanations, how-to, overviews)
    medium_signals = [
        "explain", "how does", "how do", "steps", "guide", "overview",
        "describe", "difference", "concept", "structure", "mechanism", "workflow"
    ]
    medium_hits = [s for s in medium_signals if s in q_lower]

    # Light burden indicators (quick lookups, definitions, greetings)
    light_signals = [
        "what is", "who is", "when did", "where is", "capital of",
        "define", "meaning of", "short summary", "hello", "hi", "hey"
    ]
    light_hits = [s for s in light_signals if s in q_lower]

    overall = complexity_info.get("overall_complexity") if complexity_info else None

    heavy_model = os.getenv("GROQ_HEAVY_MODEL", "openai/gpt-oss-120b")
    medium_model = os.getenv("GROQ_MEDIUM_MODEL", "qwen/qwen3.8-27b")
    light_model = os.getenv("GROQ_LIGHT_MODEL", "openai/gpt-oss-20b")

    if overall == "high" or len(heavy_hits) >= 2 or (len(heavy_hits) >= 1 and words > 15) or words > 30:
        return {
            "burden": "high",
            "model": heavy_model,
            "reason": f"High cognitive burden detected ({', '.join(heavy_hits) or f'{words} words'}); routed to strong 120B model.",
            "signals": heavy_hits,
        }
    elif overall == "medium" or len(heavy_hits) == 1 or len(medium_hits) >= 1 or words > 12 or (query.count("?") > 1):
        return {
            "burden": "medium",
            "model": medium_model,
            "reason": f"Moderate burden detected ({', '.join(medium_hits + heavy_hits) or 'analytical structure'}); routed to balanced 27B model.",
            "signals": medium_hits + heavy_hits,
        }
    else:
        return {
            "burden": "low",
            "model": light_model,
            "reason": f"Low burden factual/lookup query; routed to lightweight 20B model for high speed.",
            "signals": light_hits,
        }
