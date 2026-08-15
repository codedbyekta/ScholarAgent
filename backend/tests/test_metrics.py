"""
Unit tests for the metric formulas themselves - these run with zero
network calls and zero API keys, so they always pass in CI regardless of
whether GOOGLE_API_KEY is configured. They verify the MATH is correct;
the actual end-to-end evaluation (which does need a real API key and
network) is run separately via `python -m app.eval.run_eval`.
"""

import pytest

from app.eval.metrics import (
    matches_expected,
    precision_at_k,
    retrieval_success,
    retrieval_success_rate,
    citation_verification_accuracy,
    unsupported_claim_rate,
    latency_stats,
    aggregate_metrics,
)


def test_matches_expected_case_insensitive():
    assert matches_expected("Attention Is All You Need", ["attention is all you need"])
    assert not matches_expected("BERT: Pre-training", ["Attention Is All You Need"])


def test_precision_at_k_basic():
    titles = ["Attention Is All You Need", "Something Else", "Another Paper", "Yet Another", "Fifth Paper"]
    expected = ["Attention Is All You Need"]
    # 1 of top 5 matches -> 1/5 = 0.2
    assert precision_at_k(titles, expected, k=5) == pytest.approx(0.2)


def test_precision_at_k_empty_retrieval():
    assert precision_at_k([], ["Anything"], k=5) == 0.0


def test_retrieval_success_true_and_false():
    titles = ["Some unrelated paper", "Attention Is All You Need appendix"]
    assert retrieval_success(titles, ["Attention Is All You Need"]) is True
    assert retrieval_success(titles, ["Completely Different Paper"]) is False


def test_retrieval_success_rate():
    assert retrieval_success_rate([True, True, False, False]) == pytest.approx(0.5)
    assert retrieval_success_rate([]) == 0.0


def test_citation_verification_accuracy():
    claims = [
        {"claim": "a", "citations": [1], "verdict": "SUPPORTED"},
        {"claim": "b", "citations": [2], "verdict": "UNSUPPORTED"},
        {"claim": "c", "citations": [], "verdict": "UNSUPPORTED"},  # excluded: no citation
    ]
    # Only claims WITH citations count: 1 supported / 2 cited = 0.5
    assert citation_verification_accuracy(claims) == pytest.approx(0.5)


def test_citation_verification_accuracy_none_when_no_cited_claims():
    claims = [{"claim": "a", "citations": [], "verdict": "UNSUPPORTED"}]
    assert citation_verification_accuracy(claims) is None


def test_unsupported_claim_rate():
    claims = [
        {"claim": "a", "citations": [1], "verdict": "SUPPORTED"},
        {"claim": "b", "citations": [2], "verdict": "UNSUPPORTED"},
        {"claim": "c", "citations": [], "verdict": "UNSUPPORTED"},
    ]
    # 2 unsupported out of 3 total claims
    assert unsupported_claim_rate(claims) == pytest.approx(2 / 3)


def test_latency_stats():
    stats = latency_stats([100.0, 200.0, 300.0])
    assert stats["average_ms"] == pytest.approx(200.0)
    assert stats["min_ms"] == 100.0
    assert stats["max_ms"] == 300.0


def test_latency_stats_empty():
    stats = latency_stats([])
    assert stats["average_ms"] is None


def test_aggregate_metrics_excludes_failed_runs():
    results = [
        {
            "retrieved_titles": ["Attention Is All You Need"],
            "expected_sources": ["Attention Is All You Need"],
            "verified_claims": [{"claim": "x", "citations": [1], "verdict": "SUPPORTED"}],
            "latency_ms": 1000.0,
            "error": None,
        },
        {
            "retrieved_titles": [],
            "expected_sources": ["Whatever"],
            "verified_claims": [],
            "latency_ms": None,
            "error": "network failure",
        },
    ]
    agg = aggregate_metrics(results, top_k=5)
    assert agg["total_questions"] == 2
    assert agg["successful_runs"] == 1
    assert agg["failed_runs"] == 1
    assert agg["retrieval_precision_at_k"] == pytest.approx(0.2)
