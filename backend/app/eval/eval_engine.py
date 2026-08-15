"""
Runs the benchmark by invoking the REAL ScholarAgent LangGraph pipeline
for every question - real Gemini calls, real arXiv/Semantic Scholar
calls, real web search, real claim extraction/verification. Nothing here
is mocked, hardcoded, or manually entered.

If a run fails (missing API key, network error, etc.) that question is
recorded with an `error` field and EXCLUDED from metric averages rather
than being silently treated as a zero or a success - see metrics.py's
handling of `successful` runs, and routes_eval.py's "Not evaluated"
fallback when there are zero successful runs at all.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.agent.graph import scholar_agent_graph
from app.eval.metrics import aggregate_metrics, precision_at_k, retrieval_success, citation_verification_accuracy, unsupported_claim_rate
from app.db.sqlite_db import save_eval_run

logger = logging.getLogger(__name__)

BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "benchmark.json")


def load_benchmark() -> list[dict]:
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_single_question(question: dict, top_k: int) -> dict:
    """Executes ONE real end-to-end agent run and records everything the
    evaluation dashboard needs to show for this question."""
    session_id = f"eval-{question['id']}-{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": session_id}}

    initial_state = {
        "session_id": session_id,
        "query": question["query"],
        "chat_history": [],
        "has_uploaded_docs": False,
    }

    start = time.perf_counter()
    try:
        result = scholar_agent_graph.invoke(initial_state, config=config)
        latency_ms = (time.perf_counter() - start) * 1000

        retrieved_titles = [p["title"] for p in result.get("papers", [])]
        verified_claims = result.get("verified_claims", [])

        return {
            "id": question["id"],
            "query": question["query"],
            "expected_sources": question["expected_sources"],
            "retrieved_titles": retrieved_titles,
            "retrieved_papers": result.get("papers", []),
            "rag_chunks_used": len(result.get("rag_chunks", [])),
            "web_results_used": len(result.get("web_results", [])),
            "generated_answer": result.get("final_report", ""),
            "extracted_claims": result.get("claims", []),
            "verified_claims": verified_claims,
            "latency_ms": latency_ms,
            "error": None,
            "per_question_metrics": {
                "precision_at_k": precision_at_k(retrieved_titles, question["expected_sources"], top_k),
                "retrieval_success": retrieval_success(retrieved_titles, question["expected_sources"]),
                "citation_verification_accuracy": citation_verification_accuracy(verified_claims),
                "unsupported_claim_rate": unsupported_claim_rate(verified_claims),
                "latency_ms": latency_ms,
            },
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.exception("Evaluation run failed for question %s", question["id"])
        return {
            "id": question["id"],
            "query": question["query"],
            "expected_sources": question["expected_sources"],
            "retrieved_titles": [],
            "retrieved_papers": [],
            "rag_chunks_used": 0,
            "web_results_used": 0,
            "generated_answer": "",
            "extracted_claims": [],
            "verified_claims": [],
            "latency_ms": latency_ms,
            "error": str(exc),
            "per_question_metrics": None,
        }


def run_full_evaluation(top_k: int | None = None) -> dict:
    """Runs all 10 benchmark questions through the real pipeline, computes
    aggregate metrics, persists the run to SQLite, and returns the full
    result. This is what both `POST /api/eval/run` and the reproducible
    CLI command (`python -m app.eval.run_eval`) call."""
    top_k = top_k or settings.eval_top_k

    if not settings.google_api_key:
        logger.warning("GOOGLE_API_KEY not set - evaluation cannot run.")
        return {
            "run_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "aggregate": None,
            "results": [],
            "not_evaluated_reason": "GOOGLE_API_KEY is not configured. Set it in backend/.env to run evaluation.",
        }

    benchmark = load_benchmark()
    logger.info("Starting evaluation run over %d questions (top_k=%d)...", len(benchmark), top_k)

    results = []
    for i, question in enumerate(benchmark):
        if i > 0:
            logger.info("Waiting 60s before next question to respect API rate limits...")
            time.sleep(60)
        logger.info("Evaluating: %s", question["query"])
        results.append(_run_single_question(question, top_k))

    aggregate = aggregate_metrics(results, top_k)

    run_id = f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    save_eval_run(run_id, aggregate, results)
    logger.info("Evaluation run %s complete. Aggregate: %s", run_id, aggregate)

    return {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "aggregate": aggregate,
        "results": results,
        "not_evaluated_reason": None,
    }