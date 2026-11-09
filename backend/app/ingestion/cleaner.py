import re
import unicodedata


def clean_text(text: str) -> str:
    # Normalize Unicode characters
    text = unicodedata.normalize("NFKC", text)

    # Remove null characters
    text = text.replace("\x00", "")

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse spaces and tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()