"""
Tests the PDF -> text -> chunks pipeline. Uses a PDF generated on the fly
with PyMuPDF itself (fitz.open() + insert_text), so this test needs no
network access and no fixture files checked into the repo.
"""

import os
import tempfile

import fitz

from app.services.pdf_ingest import extract_text, chunk_text, process_pdf


def _make_sample_pdf(text: str) -> str:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    doc.save(path)
    doc.close()
    return path


def test_extract_text_returns_content():
    path = _make_sample_pdf("Retrieval-Augmented Generation improves factual accuracy.")
    try:
        text = extract_text(path)
        assert "Retrieval" in text
    finally:
        os.unlink(path)


def test_chunk_text_respects_size_and_overlap():
    text = "word " * 500  # ~2500 characters
    chunks = chunk_text(text, chunk_size=1000, overlap=150)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 1000


def test_chunk_text_empty_input():
    assert chunk_text("") == []


def test_process_pdf_end_to_end():
    path = _make_sample_pdf("Chain-of-Thought prompting improves multi-step reasoning in LLMs.")
    try:
        chunks = process_pdf(path)
        assert len(chunks) >= 1
        assert "Chain-of-Thought" in chunks[0]
    finally:
        os.unlink(path)
