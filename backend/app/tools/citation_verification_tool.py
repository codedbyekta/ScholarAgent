"""
TOOL 4 of 4: Claim-level citation verification.

This is the project's key differentiator and the backbone of the
evaluation engine. It does two LLM-powered jobs:

  1. extract_claims()  - break a generated answer into atomic factual
     claims, each tagged with the citation numbers [n] the answer used
     for it (or no citation, if the model asserted something uncited).

  2. verify_claims()   - for each claim, look up the ACTUAL text of the
     source(s) it cited and ask the LLM to judge, strictly from that
     source text, whether the claim is SUPPORTED or UNSUPPORTED.

This turns "the agent cited something" into "the citation was checked
against the real source and found accurate" - which is exactly what
Citation Verification Accuracy and Unsupported Claim Rate measure.
"""

import logging

from app.core.llm_client import generate_json

logger = logging.getLogger(__name__)

CLAIM_EXTRACTION_PROMPT = """You extract atomic factual claims from a research \
answer. Break the answer into a list of short, self-contained factual claims. \
For each claim, note which citation numbers (like [1], [2]) it relies on, if \
any. A claim with no citation number in the original text gets an empty list.

Respond ONLY as a JSON array, no prose, no markdown fences:
[{"claim": "...", "citations": [1, 2]}, {"claim": "...", "citations": []}]
"""

CLAIM_VERIFICATION_PROMPT = """You are a strict fact-checker. You are given a \
claim and the text of the source(s) it cites. Judge ONLY from the given source \
text whether the claim is accurately supported.

Respond ONLY as a JSON object, no prose, no markdown fences:
{"verdict": "SUPPORTED", "reason": "short reason, under 20 words"}
or
{"verdict": "UNSUPPORTED", "reason": "short reason, under 20 words"}

Rules:
- If the claim has no citations at all, verdict is always "UNSUPPORTED" \
with reason "no citation provided".
- If the cited source text does not actually contain evidence for the \
claim, verdict is "UNSUPPORTED".
- Only mark "SUPPORTED" if the source text clearly backs the specific \
claim made.
"""


def extract_claims(answer_markdown: str) -> list[dict]:
    """Returns [{"claim": str, "citations": [int, ...]}, ...]"""
    result = generate_json(CLAIM_EXTRACTION_PROMPT, answer_markdown, temperature=0)
    if isinstance(result, list):
        cleaned = []
        for item in result:
            if isinstance(item, dict) and "claim" in item:
                cleaned.append({"claim": item["claim"], "citations": item.get("citations", []) or []})
        return cleaned
    logger.warning("extract_claims did not return a list, got: %s", type(result))
    return []


def verify_claim(claim: str, citations: list[int], source_lookup: dict[int, str]) -> dict:
    """source_lookup maps citation number -> the actual source text
    (paper abstract, RAG chunk text, or web snippet)."""
    if not citations:
        return {"claim": claim, "citations": citations, "verdict": "UNSUPPORTED", "reason": "no citation provided"}

    source_text = "\n".join(
        f"[{n}] {source_lookup.get(n, '(source text not found)')}" for n in citations
    )
    user_prompt = f"Claim: {claim}\n\nCited source text:\n{source_text}"
    result = generate_json(CLAIM_VERIFICATION_PROMPT, user_prompt, temperature=0)

    verdict = result.get("verdict", "UNSUPPORTED") if isinstance(result, dict) else "UNSUPPORTED"
    reason = result.get("reason", "verification failed to parse") if isinstance(result, dict) else "verification failed to parse"
    if verdict not in ("SUPPORTED", "UNSUPPORTED"):
        verdict = "UNSUPPORTED"

    return {"claim": claim, "citations": citations, "verdict": verdict, "reason": reason}


def verify_claims(claims: list[dict], source_lookup: dict[int, str]) -> list[dict]:
    """Runs verify_claim for every extracted claim. Kept as sequential
    calls (not batched into one prompt) so each verdict is independently
    grounded and easy to audit/debug one claim at a time."""
    return [verify_claim(c["claim"], c["citations"], source_lookup) for c in claims]
