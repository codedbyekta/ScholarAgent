"""
POST /api/chat - the single entry point the React frontend calls. Loads
memory from SQLite, runs the real LangGraph agent, saves the new turn
back to SQLite, and returns the cited report + verified claims + trace.
Failure handling: any exception from the agent graph is caught and
returned as a clean 500 with a message, instead of crashing the process
or returning a half-built response.
"""
import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, SourceItem
from app.agent.graph import scholar_agent_graph
from app.db.sqlite_db import get_history, save_message
from app.db.chroma_store import session_has_documents
from app.tools.citation_registry import CitationRegistry
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])
@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    logger.info("Received chat request for session=%s", request.session_id)
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    history = get_history(request.session_id)
    has_docs = session_has_documents(request.session_id)
    initial_state = {
        "session_id": request.session_id,
        "query": request.query,
        "chat_history": history,
        "has_uploaded_docs": has_docs,
    }
    config = {"configurable": {"thread_id": request.session_id}}
    try:
        result = scholar_agent_graph.invoke(initial_state, config=config)
    except Exception as exc:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}") from exc
    save_message(request.session_id, "user", request.query)
    save_message(request.session_id, "assistant", result["final_report"])
    registry = CitationRegistry.from_dict(result["citation_registry"])
    sources = [SourceItem(**s) for s in registry.as_list()]
    trace = {
        "sub_questions": result.get("sub_questions", []),
        "papers_found": len(result.get("papers", [])),
        "rag_chunks_used": len(result.get("rag_chunks", [])),
        "web_results_used": len(result.get("web_results", [])),
        "web_verification_ran": result.get("needs_web_verification", False),
        "claims_extracted": len(result.get("claims", [])),
    }
    return ChatResponse(
        session_id=request.session_id,
        answer=result["final_report"],
        sources=sources,
        sub_questions=result.get("sub_questions", []),
        verified_claims=result.get("verified_claims", []),
        trace=trace,
    )