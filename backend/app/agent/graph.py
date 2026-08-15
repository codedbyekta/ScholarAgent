"""
Wires the 7 nodes into a LangGraph StateGraph. Mostly linear because a
research pipeline is naturally sequential - you need sources before you
can synthesize, and a synthesized draft before you can verify its claims.

    START -> planner -> paper_retrieval -> rag_retrieval
          -> web_verification -> synthesizer -> claim_verification
          -> citation_formatter -> END
"""

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState
from app.agent.nodes import (
    planner_node,
    paper_retrieval_node,
    rag_retrieval_node,
    web_verification_node,
    synthesizer_node,
    claim_verification_node,
    citation_formatter_node,
)

logger = logging.getLogger(__name__)


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("paper_retrieval", paper_retrieval_node)
    graph.add_node("rag_retrieval", rag_retrieval_node)
    graph.add_node("web_verification", web_verification_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("claim_verification", claim_verification_node)
    graph.add_node("citation_formatter", citation_formatter_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "paper_retrieval")
    graph.add_edge("paper_retrieval", "rag_retrieval")
    graph.add_edge("rag_retrieval", "web_verification")
    graph.add_edge("web_verification", "synthesizer")
    graph.add_edge("synthesizer", "claim_verification")
    graph.add_edge("claim_verification", "citation_formatter")
    graph.add_edge("citation_formatter", END)

    # In-memory checkpointing (per-process). Enables LangGraph's
    # thread/session-scoped run tracking. No external service needed.
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


scholar_agent_graph = build_graph()
