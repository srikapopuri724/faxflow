"""PDF rendering helpers. Faxes arrive as scanned PDFs, so we rasterize
pages to PNG before handing them to the vision model."""

from __future__ import annotations

import base64
from pathlib import Path

import pypdfium2 as pdfium


def render_pdf_to_png(path: Path, max_pages: int, scale: float = 2.0) -> list[bytes]:
    """Render up to `max_pages` pages of a PDF to PNG bytes."""
    images: list[bytes] = []
    pdf = pdfium.PdfDocument(str(path))
    try:
        n = min(len(pdf), max_pages)
        for i in range(n):
            page = pdf[i]
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            from io import BytesIO

            buf = BytesIO()
            pil_image.save(buf, format="PNG")
            images.append(buf.getvalue())
    finally:
        pdf.close()
    return images


def page_count(path: Path) -> int:
    pdf = pdfium.PdfDocument(str(path))
    try:
        return len(pdf)
    finally:
        pdf.close()


def to_base64(png_bytes: bytes) -> str:
    return base64.standard_b64encode(png_bytes).decode("ascii")
