import re


def create_chunks(
    source_units,
    document_id: str,
    chunk_size: int = 500,
    overlap: int = 75,
):
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Overlap must be between 0 and chunk size.")

    chunks = []
    chunk_index = 0

    for unit in source_units:
        text = unit["text"].strip()
        if not text:
            continue

        # Word positions preserve source traceability
        words = list(re.finditer(r"\S+", text))
        if not words:
            continue

        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))

            start_char = words[start].start()
            end_char = words[end - 1].end()
            chunk_text = text[start_char:end_char].strip()

            chunks.append(
                {
                    "chunk_id": f"{document_id}_{chunk_index}",
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "metadata": {
                        "page_number": unit.get("page_number"),
                        "paragraph_number": unit.get("paragraph_number"),
                        "start_char": start_char,
                        "end_char": end_char,
                        "word_count": end - start,
                    },
                }
            )

            chunk_index += 1

            if end == len(words):
                break

            start = end - overlap

    return chunks