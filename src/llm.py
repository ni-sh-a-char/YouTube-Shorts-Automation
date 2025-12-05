"""Lightweight LLM adapter to support multiple providers (Gemini, Groq).

This module provides a minimal `generate(prompt, model=None, **kwargs)` function
that returns an object with a `.text` attribute to be compatible with existing
call sites in the project.

Notes:
- For `llm_provider=gemini` this delegates to `google.generativeai` (existing behavior).
- For `llm_provider=groq` this will try to use an installed `groq` SDK when
  available. If the SDK is not installed, it will attempt an HTTP POST to the
  `GROQ_API_URL` (which you must set in your environment) with a Bearer token
  header `GROQ_API_KEY`.

Because Groq endpoints and SDKs can vary, this adapter intentionally keeps the
HTTP behavior simple and expects the project maintainer to verify the correct
endpoint and response parsing. The default Groq model name used here is
`gpt-oss-120b` (can be changed via `GROQ_MODEL` env var).
"""
from typing import Any, Optional
import os
import json
import requests


class LLMResponse:
    def __init__(self, text: str, raw: Any = None):
        self.text = text
        self.raw = raw


def generate(prompt: str, model: Optional[str] = None, **kwargs) -> LLMResponse:
    """Generate text from the configured LLM provider.

    Returns an LLMResponse with `.text` containing the model output.
    """
    # Deferred import to avoid heavy deps when not used
    from scripts.config import get_config

    config = get_config()
    provider = config.llm_provider

    # Default model selection
    if not model:
        model = config.groq_model if provider == 'groq' else config.gemini_model

    if provider == 'groq':
        # Use Groq SDK pattern when available (example provided by user):
        # from groq import Groq
        # client = Groq()
        # completion = client.chat.completions.create(...)
        api_key = config.groq_api_key or os.getenv('GROQ_API_KEY')
        try:
            from groq import Groq  # type: ignore
            try:
                # Create client - sdk may accept api_key param or pick from env
                client = Groq(api_key) if api_key else Groq()
            except TypeError:
                # Some SDK versions expect no args
                client = Groq()

            # Build completion parameters using kwargs defaults where appropriate
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', 1),
                max_completion_tokens=kwargs.get('max_completion_tokens', 4096),
                top_p=kwargs.get('top_p', 1),
                reasoning_effort=kwargs.get('reasoning_effort', 'medium'),
                stream=kwargs.get('stream', False),
                stop=kwargs.get('stop', None),
            )

            # First try to extract text via common attributes without iterating.
            def _extract_from_choice(obj):
                try:
                    # message.content is a common field
                    return obj.choices[0].message.content
                except Exception:
                    pass
                try:
                    return obj.choices[0].delta.content
                except Exception:
                    pass
                try:
                    return obj.choices[0].text
                except Exception:
                    pass
                return None

            text = None
            try:
                text = _extract_from_choice(completion)
            except Exception:
                text = None

            # If not found and the object looks iterable, it may be a streaming iterator.
            if not text and getattr(completion, '__iter__', None) and not isinstance(completion, (str, bytes)):
                pieces = []
                for chunk in completion:
                    # Try delta then message
                    part = None
                    try:
                        part = chunk.choices[0].delta.content
                    except Exception:
                        pass
                    if not part:
                        try:
                            part = chunk.choices[0].message.content
                        except Exception:
                            pass
                    if part:
                        pieces.append(part)
                    else:
                        # Avoid appending raw reprs; skip if nothing useful
                        continue
                if pieces:
                    text = ''.join(pieces)

            # Final fallback: stringified completion
            if text is None:
                try:
                    text = str(completion)
                except Exception:
                    text = ''

            return LLMResponse(text=str(text), raw=completion)

        except Exception:
            # Fall back to a simple HTTP POST approach if SDK not available
            api_url = config.groq_api_url or os.getenv('GROQ_API_URL')
            if not api_url:
                raise RuntimeError(
                    "Groq provider selected but `groq` SDK is not installed and `GROQ_API_URL` is not configured."
                )
            if not api_key:
                raise RuntimeError("Groq provider selected but `GROQ_API_KEY` is not set in environment.")

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
            payload = {
                'model': model,
                'input': prompt,
            }
            resp = requests.post(api_url, headers=headers, json=payload, timeout=30)
            try:
                resp.raise_for_status()
            except Exception as e:
                raise RuntimeError(f"Groq API error: {e} - {resp.text}")
            return LLMResponse(text=resp.text, raw=resp.json())

    else:
        # Default to Gemini / Google Generative AI
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as e:
            raise RuntimeError(f"Gemini provider requested but google.generativeai is not installed: {e}")

        api_key = config.gemini_api_key
        if not api_key:
            raise RuntimeError("Gemini provider selected but `GEMINI_API_KEY` / `GOOGLE_API_KEY` not set.")

        genai.configure(api_key=api_key)
        model_name = model or config.gemini_model
        model_obj = genai.GenerativeModel(model_name)
        out = model_obj.generate_content(prompt)
        # genai response objects commonly expose `.text` - normalize for compatibility
        text = getattr(out, 'text', None)
        if text is None:
            # Fallback: try to serialize object
            try:
                text = json.dumps(out)
            except Exception:
                text = str(out)
        return LLMResponse(text=str(text), raw=out)
