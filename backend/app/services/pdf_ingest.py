"""
PDF -> text -> overlapping chunks, ready for embedding. Uses PyMuPDF
(imported as `fitz`), which is faster and more reliable at text
extraction than pypdf, especially on multi-column academic papers.
"""

import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def extract_text(file_path: str) -> str:
    text_parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def process_pdf(file_path: str) -> list[str]:
    logger.info("Extracting text from %s", file_path)
    text = extract_text(file_path)
    chunks = chunk_text(text)
    logger.info("Produced %d chunks from %s", len(chunks), file_path)
    return chunks
