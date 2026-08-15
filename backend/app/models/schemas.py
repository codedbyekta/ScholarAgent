from pydantic import BaseModel
from typing import Any


class ChatRequest(BaseModel):
    session_id: str
    query: str


class SourceItem(BaseModel):
    number: int
    title: str
    url: str = ""
    type: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceItem]
    sub_questions: list[str]
    verified_claims: list[dict]
    trace: dict


class UploadResponse(BaseModel):
    session_id: str
    doc_name: str
    chunks_indexed: int


class HealthResponse(BaseModel):
    status: str
    chroma: str
    sqlite: str
    google_api_key_configured: bool


class EvalRunSummary(BaseModel):
    run_id: str
    created_at: str
    aggregate: dict


class EvalRunDetail(BaseModel):
    run_id: str | None
    created_at: str
    aggregate: dict | None
    results: list[dict]
    not_evaluated_reason: str | None = None
