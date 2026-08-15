import logging
import os
import tempfile

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.schemas import UploadResponse
from app.services.pdf_ingest import process_pdf
from app.db.chroma_store import upsert_chunks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(session_id: str = Form(...), file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    logger.info("Uploading '%s' for session %s", file.filename, session_id)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        chunks = process_pdf(tmp_path)
        count = upsert_chunks(session_id=session_id, doc_name=file.filename, chunks=chunks)
    except Exception as exc:
        logger.exception("PDF ingestion failed")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {exc}") from exc
    finally:
        os.unlink(tmp_path)

    return UploadResponse(session_id=session_id, doc_name=file.filename, chunks_indexed=count)
