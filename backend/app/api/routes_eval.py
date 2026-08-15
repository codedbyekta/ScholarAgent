"""
API surface for the Evaluation Dashboard:
  POST /api/eval/run              - runs the REAL benchmark now, blocking
                                     until all 10 questions complete
  GET  /api/eval/runs             - list past timestamped runs (summary)
  GET  /api/eval/runs/{run_id}    - full per-question breakdown for one run
  GET  /api/eval/runs/{run_id}/download?format=json|csv - downloadable report
"""

import csv
import io
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.eval.eval_engine import run_full_evaluation
from app.db.sqlite_db import list_eval_runs, get_eval_run
from app.models.schemas import EvalRunDetail

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/eval", tags=["evaluation"])


@router.post("/run", response_model=EvalRunDetail)
def run_evaluation() -> EvalRunDetail:
    """Executes the real 10-question benchmark against the live agent
    pipeline. Takes anywhere from ~30s to a few minutes depending on API
    latency - this is a real, non-mocked run, not a cached result."""
    result = run_full_evaluation()
    return EvalRunDetail(**result)


@router.get("/runs")
def get_runs() -> list[dict]:
    return list_eval_runs()


@router.get("/runs/{run_id}", response_model=EvalRunDetail)
def get_run_detail(run_id: str) -> EvalRunDetail:
    run = get_eval_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return EvalRunDetail(
        run_id=run["run_id"],
        created_at=run["created_at"],
        aggregate=run["aggregate"],
        results=run["results"],
        not_evaluated_reason=None,
    )


@router.get("/runs/{run_id}/download")
def download_run(run_id: str, format: str = "json"):
    run = get_eval_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    if format == "json":
        import json

        buf = io.BytesIO(json.dumps(run, indent=2).encode("utf-8"))
        return StreamingResponse(
            buf,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={run_id}.json"},
        )

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "question_id", "query", "expected_sources", "precision_at_k",
            "retrieval_success", "citation_verification_accuracy",
            "unsupported_claim_rate", "latency_ms", "error",
        ])
        for r in run["results"]:
            pqm = r.get("per_question_metrics") or {}
            writer.writerow([
                r["id"],
                r["query"],
                "; ".join(r.get("expected_sources", [])),
                pqm.get("precision_at_k"),
                pqm.get("retrieval_success"),
                pqm.get("citation_verification_accuracy"),
                pqm.get("unsupported_claim_rate"),
                r.get("latency_ms"),
                r.get("error") or "",
            ])
        byte_buf = io.BytesIO(buf.getvalue().encode("utf-8"))
        return StreamingResponse(
            byte_buf,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={run_id}.csv"},
        )

    raise HTTPException(status_code=400, detail="format must be 'json' or 'csv'")
