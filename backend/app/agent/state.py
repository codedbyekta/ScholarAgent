"""
The shared 'notebook' passed between LangGraph nodes. Each node reads
some fields and writes others; LangGraph merges what a node returns into
this state before calling the next node.
"""

from typing import TypedDict, Any


class AgentState(TypedDict, total=False):
    # input
    session_id: str
    query: str
    chat_history: list[dict]
    has_uploaded_docs: bool

    # planner output
    sub_questions: list[str]
    needs_web_verification: bool

    # retrieval outputs
    papers: list[dict]
    rag_chunks: list[dict]
    web_results: list[dict]

    # synthesis
    draft_answer: str
    final_report: str

    # citation verification (Tool 4)
    claims: list[dict]
    verified_claims: list[dict]

    # internal / control
    citation_registry: Any  # dict (serialized CitationRegistry) — see to_dict/from_dict
    step: str
    error: str | None
