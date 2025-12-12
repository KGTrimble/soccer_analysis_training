from __future__ import annotations

from io import BytesIO


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF (byte content).

    Uses pdfplumber (pdfminer.six) for extraction. If the PDF is scanned (image-only),
    this will likely return an empty/near-empty string (OCR not included).
    """
    if not pdf_bytes:
        return ""

    try:
        import pdfplumber  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: pdfplumber. Install requirements.txt first."
        ) from exc

    text_parts: list[str] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)

    return "\n\n".join(text_parts).strip()

