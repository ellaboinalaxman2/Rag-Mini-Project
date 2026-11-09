import re

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "of", "to", "in", "on", "at", "for", "with", "by",
    "from", "as", "and", "or", "but", "how", "what", "which",
    "who", "whom", "whose", "when", "where", "why", "does", "do",
    "did", "has", "have", "had", "can", "could", "would", "should",
    "will", "shall", "may", "might", "must", "this", "that",
    "these", "those", "it", "its", "their", "there", "here",
    "explain", "describe", "tell", "me", "about", "between",
    "through", "via", "connected", "connection", "relationship",
    "relate", "related",
}


def preprocess_query(query: str) -> str:
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")
    cleaned = re.sub(r"\s+", " ", query.strip())
    return cleaned


def extract_keywords(query: str) -> list[str]:
    """Extract meaningful content words from a query."""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_.]*", query)
    keywords = []
    seen = set()

    for word in words:
        lower = word.lower()
        if lower in STOPWORDS:
            continue
        if len(lower) < 2:
            continue
        if lower in seen:
            continue
        seen.add(lower)
        keywords.append(word)

    return keywords


def extract_candidate_phrases(query: str) -> list[str]:
    """
    Return full candidate phrases that may match multi-word entity names.
    Simple approach: individual keywords + adjacent bigrams + trigrams.
    """
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_.]*", query)
    keywords = extract_keywords(query)

    phrases = set()

    for kw in keywords:
        phrases.add(kw)

    # Build n-grams (2 and 3 words) skipping pure stopwords at edges
    tokens = [w for w in words if w]
    for n in (2, 3):
        for i in range(len(tokens) - n + 1):
            window = tokens[i : i + n]
            if not any(w.lower() in STOPWORDS for w in window):
                phrases.add(" ".join(window))

    return list(phrases)