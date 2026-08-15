from app.eval.eval_engine import load_benchmark


def test_benchmark_has_exactly_ten_questions():
    benchmark = load_benchmark()
    assert len(benchmark) == 10


def test_every_question_has_required_fields():
    benchmark = load_benchmark()
    for q in benchmark:
        assert "id" in q
        assert "query" in q and len(q["query"]) > 0
        assert "expected_sources" in q and len(q["expected_sources"]) > 0


def test_question_ids_are_unique():
    benchmark = load_benchmark()
    ids = [q["id"] for q in benchmark]
    assert len(ids) == len(set(ids))
