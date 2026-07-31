from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Google Gemini exposes an OpenAI-compatible Chat Completions endpoint, so the
# same ChatOpenAI client works by pointing base_url at it. Gemini's free tier
# allows a far higher tokens-per-minute budget than Groq's, which suits this
# pipeline's parallel fan-out (spec / analysis / spec_graph run concurrently).
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Single production model for every agent in the pipeline. Each graph node calls
# build_llm() with only a temperature; they all route to one model so that
# provider selection lives in exactly one place. gemini-2.0-flash is fast and
# has generous free-tier throughput.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def build_llm(temperature: float, model_name: str | None = None) -> ChatOpenAI:
    """Build a Gemini-backed chat model via the OpenAI-compatible endpoint.

    Every agent in the pipeline routes through a single Gemini model so provider
    selection lives in exactly one place. ``model_name`` may be supplied to
    override the default for a specific node, but is normally left unset.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in the environment.")
    return ChatOpenAI(
        model=model_name or GEMINI_MODEL,
        api_key=api_key,
        base_url=GEMINI_BASE_URL,
        temperature=temperature,
        timeout=90,
        max_retries=2,
    )
