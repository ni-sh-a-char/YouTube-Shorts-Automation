"""Live tests for configured LLM provider (Gemini or Groq).

These tests are intended for local development only and will be skipped when
required credentials are not set.
"""
from scripts.config import get_config
import pytest


def test_llm_key_present():
    cfg = get_config()
    provider = cfg.llm_provider
    if provider == 'groq':
        key = cfg.groq_api_key
        assert key and key.strip(), "GROQ_API_KEY not set in environment or .env"
    else:
        key = cfg.gemini_api_key
        assert key and key.strip(), "GEMINI_API_KEY / GOOGLE_API_KEY not set in environment or .env"


def test_llm_reachable():
    cfg = get_config()
    from src.llm import generate as llm_generate

    provider = cfg.llm_provider
    if provider == 'groq' and not cfg.groq_api_key:
        pytest.skip("GROQ_API_KEY not set; skipping live Groq API test")
    if provider == 'gemini' and not cfg.gemini_api_key:
        pytest.skip("GEMINI_API_KEY / GOOGLE_API_KEY not set; skipping live Gemini API test")

    model_name = cfg.groq_model if provider == 'groq' else cfg.gemini_model
    try:
        resp = llm_generate("Say 'Hello'", model=model_name)
    except Exception as exc:
        pytest.fail(f"Error contacting LLM provider '{provider}': {exc}")

    assert getattr(resp, 'text', None), f"No text returned from {provider} provider"
