import logging

from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.core.config import settings
from app.db.chroma_store import get_client as get_chroma_client
from app.db.sqlite_db import get_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    chroma_status = "ok"
    try:
        get_chroma_client().heartbeat()
    except Exception as exc:
        chroma_status = f"error: {exc}"

    sqlite_status = "ok"
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
    except Exception as exc:
        sqlite_status = f"error: {exc}"

    overall = "ok" if chroma_status == "ok" and sqlite_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        chroma=chroma_status,
        sqlite=sqlite_status,
        google_api_key_configured=bool(settings.google_api_key),
    )
