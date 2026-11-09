from io import BytesIO

import fitz  # PyMuPDF
from docx import Document


def extract_pdf(content: bytes):
    pages = []
    pdf = fitz.open(stream=content, filetype="pdf")
    try:
        if pdf.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")

        for page_index, page in enumerate(pdf):
            text = page.get_text("text")
            if text.strip():
                pages.append(
                    {
                        "page_number": page_index + 1,
                        "paragraph_number": None,
                        "text": text,
                    }
                )
    finally:
        pdf.close()

    if not pages:
        raise ValueError(
            "No extractable text found. This PDF may require OCR."
        )

    return pages


def extract_docx(content: bytes):
    document = Document(BytesIO(content))
    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    if not paragraphs:
        raise ValueError("No extractable text found in DOCX.")

    return [
        {
            "page_number": None,
            "paragraph_number": None,
            "text": "\n".join(paragraphs),
        }
    ]


def extract_document(filename: str, content: bytes):
    extension = filename.lower().rsplit(".", 1)[-1]

    if extension == "pdf":
        return extract_pdf(content)
    if extension == "docx":
        return extract_docx(content)

    raise ValueError("Unsupported file type for extraction.")