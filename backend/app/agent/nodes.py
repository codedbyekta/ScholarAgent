"""
Each function here is one LangGraph node: (state) -> dict of state
updates. Order matches how they run in the graph (see graph.py):

  planner -> paper_retrieval -> rag_retrieval -> web_verification
  -> synthesizer -> claim_verification -> citation_formatter

Exactly 4 tools are used across this pipeline:
  Tool 1 (paper_search_tool)          -> paper_retrieval_node
  Tool 2 (rag_tool)                   -> rag_retrieval_node
  Tool 3 (web_search_tool)            -> web_verification_node
  Tool 4 (citation_verification_tool) -> claim_verification_node
"""

import logging
import time

from app.core.llm_client import generate_text, generate_json
from app.agent.state import AgentState
from app.agent.prompts import PLANNER_SYSTEM_PROMPT, SYNTHESIS_SYSTEM_PROMPT
from app.tools.paper_search_tool import search_papers
from app.tools.rag_tool import rag_search
from app.tools.web_search_tool import web_search
from app.tools.citation_verification_tool import extract_claims, verify_claims
from app.tools.citation_registry import CitationRegistry, build_report

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NODE 1: PLANNER (LLM, no tool)
# ---------------------------------------------------------------------------
def planner_node(state: AgentState) -> dict:
    logger.info("[planner_node] planning for query: %s", state["query"])
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in state.get("chat_history", [])[-6:])
    user_prompt = f"Chat history:\n{history_text}\n\nCurrent question: {state['query']}"

    result = generate_json(PLANNER_SYSTEM_PROMPT, user_prompt, temperature=0)
    if isinstance(result, dict) and result.get("sub_questions"):
        sub_questions = result["sub_questions"]
        needs_web = bool(result.get("needs_web_verification", True))
    else:
        logger.warning("Planner output invalid, falling back to single sub-question.")
        sub_questions = [state["query"]]
        needs_web = True

    return {"sub_questions": sub_questions, "needs_web_verification": needs_web, "step": "planned"}


# ---------------------------------------------------------------------------
# NODE 2: PAPER RETRIEVAL - Tool 1 (arXiv + Semantic Scholar)
# ---------------------------------------------------------------------------
def paper_retrieval_node(state: AgentState) -> dict:
    logger.info("[paper_retrieval_node] searching papers for %d sub-questions", len(state["sub_questions"]))
    all_papers, seen = [], set()
    for sq in state["sub_questions"]:
        for paper in search_papers(sq):
            key = paper["title"].lower().strip()
            if key and key not in seen:
                seen.add(key)
                all_papers.append(paper)
    return {"papers": all_papers[:12], "step": "papers_retrieved"}


# ---------------------------------------------------------------------------
# NODE 3: RAG RETRIEVAL - Tool 2 (Chroma, user's own PDFs)
# ---------------------------------------------------------------------------
def rag_retrieval_node(state: AgentState) -> dict:
    if not state.get("has_uploaded_docs"):
        logger.info("[rag_retrieval_node] no uploaded docs for this session, skipping.")
        return {"rag_chunks": [], "step": "rag_retrieved"}

    logger.info("[rag_retrieval_node] searching uploaded documents")
    chunks = []
    for sq in state["sub_questions"]:
        chunks.extend(rag_search(state["session_id"], sq, top_k=4))
    return {"rag_chunks": chunks[:10], "step": "rag_retrieved"}


# ---------------------------------------------------------------------------
# NODE 4: WEB VERIFICATION - Tool 3 (DuckDuckGo/Tavily)
# ---------------------------------------------------------------------------
def web_verification_node(state: AgentState) -> dict:
    if not state.get("needs_web_verification"):
        logger.info("[web_verification_node] not time-sensitive, skipping.")
        return {"web_results": [], "step": "web_verified"}

    logger.info("[web_verification_node] verifying recency via web search")
    results = []
    for sq in state["sub_questions"]:
        results.extend(web_search(sq))
    return {"web_results": results[:8], "step": "web_verified"}


# ---------------------------------------------------------------------------
# NODE 5: SYNTHESIZER (LLM + deterministic citation registry)
# ---------------------------------------------------------------------------
def synthesizer_node(state: AgentState) -> dict:
    logger.info("[synthesizer_node] synthesizing answer")
    registry = CitationRegistry()
    source_blocks = []

    for paper in state.get("papers", []):
        num = registry.register(paper["title"], paper.get("url", ""), f"Paper - {paper['source']}", paper.get("abstract", ""))
        source_blocks.append(f"[{num}] PAPER: {paper['title']}\nAbstract: {paper.get('abstract', '')}\n")

    for chunk in state.get("rag_chunks", []):
        num = registry.register(chunk["doc_name"], "", "Your uploaded document", chunk["text"])
        source_blocks.append(f"[{num}] YOUR DOCUMENT ({chunk['doc_name']}): {chunk['text']}\n")

    for web in state.get("web_results", []):
        num = registry.register(web["title"], web.get("url", ""), "Web", web.get("snippet", ""))
        source_blocks.append(f"[{num}] WEB: {web['title']}\n{web.get('snippet', '')}\n")

    sources_text = "\n".join(source_blocks) if source_blocks else "No sources were found."
    user_prompt = f"Original question: {state['query']}\n\nSOURCES:\n{sources_text}"

    draft = generate_text(SYNTHESIS_SYSTEM_PROMPT, user_prompt, temperature=0.3)

    return {"draft_answer": draft, "citation_registry": registry.to_dict(), "step": "synthesized"}


# ---------------------------------------------------------------------------
# NODE 6: CLAIM VERIFICATION - Tool 4 (citation_verification_tool)
# ---------------------------------------------------------------------------
def claim_verification_node(state: AgentState) -> dict:
    logger.info("[claim_verification_node] extracting and verifying claims")
    registry: CitationRegistry = CitationRegistry.from_dict(state["citation_registry"])

    claims = extract_claims(state["draft_answer"])
    verified = verify_claims(claims, registry.source_lookup())

    return {"claims": claims, "verified_claims": verified, "step": "claims_verified"}


# ---------------------------------------------------------------------------
# NODE 7: CITATION FORMATTER (deterministic, no LLM)
# ---------------------------------------------------------------------------
def citation_formatter_node(state: AgentState) -> dict:
    logger.info("[citation_formatter_node] building final report")
    registry: CitationRegistry = CitationRegistry.from_dict(state["citation_registry"])
    final_report = build_report(state["draft_answer"], registry)
    return {"final_report": final_report, "step": "done"}