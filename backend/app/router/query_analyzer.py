"""
Extract structural features from a query: keywords, entity-like tokens,
sentence shape, and keyword-category hits.
"""
import re

from app.router.routing_policy import (
    RELATIONSHIP_KEYWORDS,
    SEMANTIC_KEYWORDS,
    MULTIHOP_KEYWORDS,
    COMPARISON_KEYWORDS,
    SUMMARY_KEYWORDS,
)

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "of", "to", "in", "on", "at", "for", "with", "by",
    "from", "as", "and", "or", "but", "how", "what", "which",
    "who", "whom", "whose", "when", "where", "why", "does", "do",
    "did", "has", "have", "had", "can", "could", "would", "should",
    "will", "shall", "may", "might", "must", "this", "that",
    "these", "those", "it", "its", "their", "there", "here",
    "me", "my", "we", "our", "you", "your", "they", "them",
}


def _tokens(query: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_.]*", query)


def _detect_phrases(query_lower: str, keyword_set: set) -> list[str]:
    hits = []
    for kw in keyword_set:
        # word-boundary check for multi-word phrases
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, query_lower):
            hits.append(kw)
    return hits


def _extract_entity_candidates(tokens: list[str]) -> list[str]:
    """
    Heuristic entity candidates:
      - Capitalized tokens not at sentence start (proper nouns)
      - Alphanumeric tokens with digits (Product1, S3, EC2)
      - ALL-CAPS acronyms of length >= 2 (AWS, API)
    """
    candidates = []
    seen = set()

    for i, tok in enumerate(tokens):
        lower = tok.lower()
        if lower in STOPWORDS or len(tok) < 2:
            continue

        is_capitalized = tok[0].isupper()
        is_acronym = tok.isupper() and len(tok) >= 2 and tok.isalpha()
        has_digit = any(c.isdigit() for c in tok)

        # skip the very first token being just sentence-case
        if i == 0 and is_capitalized and not is_acronym and not has_digit:
            continue

        if (is_capitalized and not lower in STOPWORDS) or is_acronym or has_digit:
            key = lower
            if key not in seen:
                seen.add(key)
                candidates.append(tok)

    return candidates


def analyze_query(query: str) -> dict:
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    cleaned = re.sub(r"\s+", " ", query.strip())
    lower = cleaned.lower()
    tokens = _tokens(cleaned)
    content_tokens = [t for t in tokens if t.lower() not in STOPWORDS]

    relationship_hits = _detect_phrases(lower, RELATIONSHIP_KEYWORDS)
    semantic_hits = _detect_phrases(lower, SEMANTIC_KEYWORDS)
    multihop_hits = _detect_phrases(lower, MULTIHOP_KEYWORDS)
    comparison_hits = _detect_phrases(lower, COMPARISON_KEYWORDS)
    summary_hits = _detect_phrases(lower, SUMMARY_KEYWORDS)

    entity_candidates = _extract_entity_candidates(tokens)

    return {
        "query": cleaned,
        "length": len(cleaned),
        "word_count": len(tokens),
        "content_word_count": len(content_tokens),
        "entity_candidates": entity_candidates,
        "entity_count": len(entity_candidates),
        "relationship_hits": relationship_hits,
        "semantic_hits": semantic_hits,
        "multihop_hits": multihop_hits,
        "comparison_hits": comparison_hits,
        "summary_hits": summary_hits,
        "has_question_word": any(
            lower.startswith(w + " ")
            for w in ("what", "who", "how", "why", "when", "where", "which")
        ),
    }