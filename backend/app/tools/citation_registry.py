"""
Deterministic citation numbering + report assembly. This is NOT one of
the 4 agent tools - it's plain formatting code the synthesizer node uses
so citation numbers are assigned reliably in code, never left to the LLM
to get right on its own (a common source of malformed/hallucinated
citations in naive RAG systems).
"""
class CitationRegistry:
    def __init__(self):
        self._sources: list[dict] = []
        self._seen: dict[str, int] = {}
    def register(self, title: str, url: str, source_type: str, text: str = "") -> int:
        key = url or title
        if key in self._seen:
            return self._seen[key]
        self._sources.append({"title": title, "url": url, "type": source_type, "text": text})
        number = len(self._sources)
        self._seen[key] = number
        return number
    def render_references(self) -> str:
        if not self._sources:
            return "No sources were cited."
        lines = ["## References"]
        for i, src in enumerate(self._sources, start=1):
            url_part = f" — {src['url']}" if src["url"] else ""
            lines.append(f"[{i}] {src['title']} ({src['type']}){url_part}")
        return "\n".join(lines)
    def as_list(self) -> list[dict]:
        return [{"number": i + 1, **{k: v for k, v in s.items() if k != "text"}} for i, s in enumerate(self._sources)]
    def source_lookup(self) -> dict[int, str]:
        """number -> source text, used by the citation verification tool."""
        return {i + 1: s["text"] for i, s in enumerate(self._sources)}
    def to_dict(self) -> dict:
        return {"sources": self._sources, "seen": self._seen}
    @classmethod
    def from_dict(cls, data: dict) -> "CitationRegistry":
        obj = cls()
        obj._sources = data.get("sources", [])
        obj._seen = data.get("seen", {})
        return obj
def build_report(answer_markdown: str, registry: CitationRegistry) -> str:
    return f"{answer_markdown.strip()}\n\n{registry.render_references()}"