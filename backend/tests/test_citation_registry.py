from app.tools.citation_registry import CitationRegistry, build_report


def test_register_assigns_incrementing_numbers():
    reg = CitationRegistry()
    n1 = reg.register("Paper A", "http://a.com", "Paper", "text a")
    n2 = reg.register("Paper B", "http://b.com", "Paper", "text b")
    assert n1 == 1
    assert n2 == 2


def test_register_same_url_reuses_number():
    reg = CitationRegistry()
    n1 = reg.register("Paper A", "http://a.com", "Paper", "text a")
    n2 = reg.register("Paper A duplicate call", "http://a.com", "Paper", "text a")
    assert n1 == n2
    assert len(reg.as_list()) == 1


def test_render_references_format():
    reg = CitationRegistry()
    reg.register("Attention Is All You Need", "http://arxiv.org/abs/1706.03762", "Paper - arXiv", "abstract text")
    rendered = reg.render_references()
    assert "[1] Attention Is All You Need" in rendered
    assert "http://arxiv.org/abs/1706.03762" in rendered


def test_source_lookup_maps_number_to_text():
    reg = CitationRegistry()
    reg.register("Doc", "", "Your uploaded document", "the actual chunk text")
    lookup = reg.source_lookup()
    assert lookup[1] == "the actual chunk text"


def test_build_report_appends_references():
    reg = CitationRegistry()
    reg.register("Paper A", "http://a.com", "Paper", "text")
    report = build_report("This is the answer body [1].", reg)
    assert "This is the answer body [1]." in report
    assert "## References" in report
