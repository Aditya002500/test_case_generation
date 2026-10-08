from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Provider configurations
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://localhost:11434/v1")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "qwen2.5-coder:7b")


def build_llm(temperature: float, model_name: str | None = None) -> ChatOpenAI:
    """Build an LLM client via OpenAI-compatible endpoint.

    Supports:
      1. Local models via Ollama / LM Studio / vLLM (set LLM_PROVIDER=local or ollama)
      2. Google Gemini (set LLM_PROVIDER=gemini)
      3. Groq Cloud (set LLM_PROVIDER=groq or defaults if GROQ_CLOUD_API_KEY is present)
    """
    provider = os.getenv("LLM_PROVIDER", "").lower()
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_CLOUD_API_KEY")

    # Local model support (Ollama, LM Studio, vLLM, llama.cpp)
    if provider in ("local", "ollama", "lmstudio", "vllm"):
        return ChatOpenAI(
            model=model_name or LOCAL_MODEL,
            api_key=os.getenv("LOCAL_API_KEY", "ollama"),
            base_url=LOCAL_BASE_URL,
            temperature=temperature,
            timeout=180,
            max_retries=2,
        )

    # If explicitly requested Gemini and key is present
    if provider == "gemini" and gemini_key:
        return ChatOpenAI(
            model=model_name or GEMINI_MODEL,
            api_key=gemini_key,
            base_url=GEMINI_BASE_URL,
            temperature=temperature,
            timeout=90,
            max_retries=2,
        )

    # If explicitly requested Groq or if Groq is available
    if (provider == "groq" or groq_key) and groq_key:
        return ChatOpenAI(
            model=model_name or GROQ_MODEL,
            api_key=groq_key,
            base_url=GROQ_BASE_URL,
            temperature=temperature,
            timeout=90,
            max_retries=2,
        )

    # Fallback to Gemini
    if gemini_key:
        return ChatOpenAI(
            model=model_name or GEMINI_MODEL,
            api_key=gemini_key,
            base_url=GEMINI_BASE_URL,
            temperature=temperature,
            timeout=90,
            max_retries=2,
        )

    # Fallback to local endpoint
    return ChatOpenAI(
        model=model_name or LOCAL_MODEL,
        api_key="ollama",
        base_url=LOCAL_BASE_URL,
        temperature=temperature,
        timeout=180,
        max_retries=2,
    )
