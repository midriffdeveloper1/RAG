

from pathlib import Path

import docx  # python-docx
from pypdf import PdfReader

from app.core.config import get_settings

settings = get_settings()


class UnsupportedFileTypeError(ValueError):
    pass


def extract_text(file_path: str, file_type: str) -> str:
   
    if file_type == "pdf":
        return _extract_pdf_text(file_path)
    if file_type == "docx":
        return _extract_docx_text(file_path)
    if file_type == "doc":
        # TODO: legacy .doc isn't supported by python-docx. Either:
        #   (a) reject .doc at upload time (simplest), or
        #   (b) shell out to `libreoffice --headless --convert-to docx`
        #       before extraction.
        raise UnsupportedFileTypeError(
            
        )
    raise UnsupportedFileTypeError(f"Unsupported file type: {file_type}")


def _extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip()


def _extract_docx_text(file_path: str) -> str:
    document = docx.Document(file_path)
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]

    # Tables often hold pricing/hours in real documents — include them too.
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    return "\n\n".join(paragraphs).strip()


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # Prefer breaking at the last paragraph/sentence boundary in range.
        if end < text_length:
            boundary = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if boundary != -1 and boundary > start:
                end = boundary + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break
        start = max(end - chunk_overlap, start + 1)  # always make forward progress

    return chunks


def infer_file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix