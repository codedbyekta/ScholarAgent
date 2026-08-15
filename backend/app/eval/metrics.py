"""
All 5 required metrics, computed purely from real pipeline run data -
never hardcoded. Each function's docstring states the exact formula, and
the README repeats these formulas for interview defensibility.
"""


def matches_expected(title: str, expected_sources: list[str]) -> bool:
    """A retrieved paper 'matches' ground truth if any expected keyword
    is a case-insensitive substring of its title."""
    title_lower = title.lower()
    return any(exp.lower() in title_lower for exp in expected_sources)


def precision_at_k(retrieved_titles: list[str], expected_sources: list[str], k: int) -> float:
    """
    Retrieval Precision@K = (# of the top-K retrieved papers that match
    an expected ground-truth source) / K

    Example: K=5, and 2 of the top 5 retrieved papers match an expected
    seminal paper title -> Precision@5 = 2 / 5 = 0.4
    """
    top_k = retrieved_titles[:k]
    if not top_k:
        return 0.0
    matches = sum(1 for t in top_k if matches_expected(t, expected_sources))
    return matches / k


def retrieval_success(retrieved_titles: list[str], expected_sources: list[str]) -> bool:
    """
    A single question 'succeeds' at retrieval if AT LEAST ONE retrieved
    paper (anywhere in the retrieved list, not just top-K) matches an
    expected ground-truth source.
    """
    return any(matches_expected(t, expected_sources) for t in retrieved_titles)


def retrieval_success_rate(per_question_success: list[bool]) -> float:
    """
    Retrieval Success Rate = (# questions with retrieval_success = True)
    / (total # questions)
    """
    if not per_question_success:
        return 0.0
    return sum(per_question_success) / len(per_question_success)


def citation_verification_accuracy(verified_claims: list[dict]) -> float | None:
    """
    Citation Verification Accuracy = (# claims WITH at least one citation
    that were verdict=SUPPORTED) / (# claims WITH at least one citation)

    Returns None (not a number) if there were zero cited claims to judge,
    so the caller can display "Not evaluated" instead of a fake 0% or 100%.
    """
    cited_claims = [c for c in verified_claims if c.get("citations")]
    if not cited_claims:
        return None
    supported = sum(1 for c in cited_claims if c["verdict"] == "SUPPORTED")
    return supported / len(cited_claims)


def unsupported_claim_rate(verified_claims: list[dict]) -> float | None:
    """
    Unsupported Claim Rate = (# claims with verdict=UNSUPPORTED, INCLUDING
    claims that had no citation at all) / (total # claims extracted)

    Returns None if there were zero claims extracted at all.
    """
    if not verified_claims:
        return None
    unsupported = sum(1 for c in verified_claims if c["verdict"] == "UNSUPPORTED")
    return unsupported / len(verified_claims)


def latency_stats(latencies_ms: list[float]) -> dict:
    """
    average_ms = sum(latencies) / count
    min_ms / max_ms = the fastest / slowest single question run

    Returns all None if no successful runs were timed.
    """
    if not latencies_ms:
        return {"average_ms": None, "min_ms": None, "max_ms": None}
    return {
        "average_ms": sum(latencies_ms) / len(latencies_ms),
        "min_ms": min(latencies_ms),
        "max_ms": max(latencies_ms),
    }


def aggregate_metrics(per_question_results: list[dict], top_k: int) -> dict:
    """
    Combines every per-question result into the final Evaluation
    Dashboard summary. `per_question_results` items are expected to have:
      retrieved_titles, expected_sources, verified_claims, latency_ms, error
    """
    successful = [r for r in per_question_results if not r.get("error")]

    precisions = [precision_at_k(r["retrieved_titles"], r["expected_sources"], top_k) for r in successful]
    successes = [retrieval_success(r["retrieved_titles"], r["expected_sources"]) for r in successful]

    all_claims = [c for r in successful for c in r.get("verified_claims", [])]

    latencies = [r["latency_ms"] for r in successful if r.get("latency_ms") is not None]

    return {
        "total_questions": len(per_question_results),
        "successful_runs": len(successful),
        "failed_runs": len(per_question_results) - len(successful),
        "top_k": top_k,
        "retrieval_precision_at_k": (sum(precisions) / len(precisions)) if precisions else None,
        "retrieval_success_rate": retrieval_success_rate(successes) if successes else None,
        "citation_verification_accuracy": citation_verification_accuracy(all_claims),
        "unsupported_claim_rate": unsupported_claim_rate(all_claims),
        "latency": latency_stats(latencies),
        "total_claims_evaluated": len(all_claims),
    }
