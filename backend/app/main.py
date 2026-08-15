"""
Run locally with:
    cd backend
    uvicorn app.main:app --reload

On Render, the start command is the same (see render.yaml).
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.sqlite_db import init_db
from app.api import routes_chat, routes_documents, routes_health, routes_eval

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ScholarAgent API",
    description="Autonomous research paper assistant powered by LangGraph + Gemini, with a built-in quantifiable evaluation engine.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_chat.router)
app.include_router(routes_documents.router)
app.include_router(routes_health.router)
app.include_router(routes_eval.router)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Starting ScholarAgent API (env=%s)...", settings.app_env)
    init_db()
    if not settings.google_api_key:
        logger.warning("GOOGLE_API_KEY is not set. Chat and evaluation will fail until it is configured in backend/.env")
    logger.info("Startup complete.")


@app.get("/")
def root():
    return {"service": "ScholarAgent API", "docs": "/docs"}
