"""
Thin wrapper around the `google-genai` SDK. Every LLM call and every
embedding call in the whole project goes through this one file - if
Google changes their SDK signature, this is the only place to fix.

We use the SDK directly (not a LangChain LLM wrapper) because the task
specifically calls for the current Google GenAI SDK, and LangGraph only
needs a plain Python function per node - it doesn't require a LangChain
LLM object.
"""

import json
import logging

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.google_api_key:
            logger.warning("GOOGLE_API_KEY is not set - LLM calls will fail until it is configured.")
        _client = genai.Client(api_key=settings.google_api_key)
    return _client


def generate_text(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """Plain-text generation. Used by the synthesizer and reflection nodes."""
    client = get_client()
    response = client.models.generate_content(
        model=settings.llm_model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=2048,
        ),
    )
    return (response.text or "").strip()


def generate_json(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> dict | list:
    """JSON-mode generation. Used by the planner, claim extractor, and
    citation verifier, which all need structured (parseable) output
    rather than free text."""
    client = get_client()
    response = client.models.generate_content(
        model=settings.llm_model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )
    raw = (response.text or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Model did not return valid JSON, raw output: %s", raw[:200])
        return {}


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Embed a single piece of text using Gemini's embedding model.
    task_type differs for what you're storing (RETRIEVAL_DOCUMENT) vs
    what you're querying with (RETRIEVAL_QUERY) - Gemini's embedding
    model uses this to produce asymmetric, better-matching vectors."""
    client = get_client()
    result = client.models.embed_content(
        model=settings.embedding_model,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return list(result.embeddings[0].values)


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Batch helper - embeds a list of texts one by one. Kept simple and
    explicit rather than relying on batch-endpoint quirks that vary
    between SDK versions."""
    return [embed_text(t, task_type=task_type) for t in texts]
