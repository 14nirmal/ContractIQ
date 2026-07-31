"""
ContractIQ — LiteLLM Gateway

Unified interface for calling multiple LLM providers (Gemini, Groq/Qwen, Groq/Llama, Groq/DeepSeek)
with retry logic, token tracking, and error handling.
"""

import logging
import time
from typing import Any

import builtins
import functools
import pathlib
import sys
import types

# ── Fix 1: Enterprise module patch for litellm 1.67.4 bug ─────
if "enterprise" not in sys.modules:
    enterprise = types.ModuleType("enterprise")
    enterprise_hooks = types.ModuleType("enterprise.enterprise_hooks")
    session_handler = types.ModuleType("enterprise.enterprise_hooks.session_handler")
    session_handler.ChatCompletionSession = None
    session_handler._ENTERPRISE_ResponsesSessionHandler = None
    sys.modules["enterprise"] = enterprise
    sys.modules["enterprise.enterprise_hooks"] = enterprise_hooks
    sys.modules["enterprise.enterprise_hooks.session_handler"] = session_handler

# ── Fix 2: Windows UTF-8 File Encoding Patch ──────────────────
_builtin_open = builtins.open


@functools.wraps(_builtin_open)
def _utf8_open(*args, **kwargs):
    mode = kwargs.get("mode", args[1] if len(args) > 1 else "r")
    if "b" not in str(mode) and "encoding" not in kwargs:
        kwargs["encoding"] = "utf-8"
    return _builtin_open(*args, **kwargs)


builtins.open = _utf8_open

_orig_path_open = pathlib.Path.open


def _utf8_path_open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
    if "b" not in mode and encoding is None:
        encoding = "utf-8"
    return _orig_path_open(self, mode=mode, buffering=buffering, encoding=encoding, errors=errors, newline=newline)


pathlib.Path.open = _utf8_path_open

try:
    from importlib.resources import _adapters
    _orig_spec_open = _adapters.CompatibilityFiles.SpecPath.open
    def _utf8_spec_open(self, mode="r", *args, **kwargs):
        if "b" not in mode and "encoding" not in kwargs:
            kwargs["encoding"] = "utf-8"
        return _orig_spec_open(self, mode, *args, **kwargs)
    _adapters.CompatibilityFiles.SpecPath.open = _utf8_spec_open
except Exception:
    pass

import litellm
# ── End Windows & Package Fixes ───────────────────────────────

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = False

# Set API keys for providers
litellm.api_key = settings.GOOGLE_API_KEY


# ─────────────────────────────────────────────
# Model Registry
# ─────────────────────────────────────────────
MODELS = {
    "gemini": "gemini/gemini-2.0-flash",
    "llama": "groq/llama-3.3-70b-versatile",
    "qwen": "groq/llama-3.1-8b-instant",
    "deepseek": "groq/llama-3.3-70b-versatile",
}

# Provider-specific API keys
PROVIDER_KEYS = {
    "gemini": settings.GOOGLE_API_KEY,
    "groq": settings.GROQ_API_KEY,
}


def _get_api_key(model_name: str) -> str:
    """Resolve the API key for a given model alias."""
    if model_name == "gemini":
        return PROVIDER_KEYS["gemini"]
    return PROVIDER_KEYS["groq"]


def _get_provider(model_name: str) -> str:
    """Resolve the provider name for a given model alias."""
    if model_name == "gemini":
        return "google"
    return "groq"


# ─────────────────────────────────────────────
# Core LLM Call
# ─────────────────────────────────────────────
def call_llm(
    model_name: str,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 4096,
    response_format: dict | None = None,
    fallback_model: str | None = "deepseek",
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Call an LLM through LiteLLM with retry and fallback logic.

    Args:
        model_name: Model alias key from MODELS dict (gemini, qwen, llama, deepseek)
        messages: Chat messages in OpenAI format
        temperature: Sampling temperature
        max_tokens: Maximum output tokens
        response_format: Optional JSON schema for structured output
        fallback_model: Model alias to fall back to on failure
        max_retries: Number of retries before falling back

    Returns:
        dict with keys: content, model, provider, tokens_in, tokens_out, latency_ms
    """
    model_id = MODELS.get(model_name, model_name)
    api_key = _get_api_key(model_name)
    provider = _get_provider(model_name)

    # Build kwargs
    kwargs = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "api_key": api_key,
    }

    if response_format:
        kwargs["response_format"] = response_format

    # Retry loop
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            response = litellm.completion(**kwargs)
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage
            usage = response.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0

            content = response.choices[0].message.content

            logger.info(
                f"LLM call success: model={model_name}, "
                f"tokens_in={tokens_in}, tokens_out={tokens_out}, "
                f"latency={latency_ms}ms"
            )

            return {
                "content": content,
                "model": model_id,
                "model_name": model_name,
                "provider": provider,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            last_error = e
            logger.warning(
                f"LLM call failed (attempt {attempt + 1}/{max_retries + 1}): "
                f"model={model_name}, error={str(e)}"
            )
            if attempt < max_retries:
                # Exponential backoff
                wait_time = (2 ** attempt) * 0.5
                time.sleep(wait_time)

    # All retries exhausted — try fallback
    if fallback_model and fallback_model != model_name:
        logger.info(f"Falling back from {model_name} to {fallback_model}")
        return call_llm(
            model_name=fallback_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            fallback_model=None,  # Prevent infinite fallback
            max_retries=1,
        )

    # Complete failure
    raise RuntimeError(
        f"LLM call failed after {max_retries + 1} attempts with fallback: {last_error}"
    )


def call_llm_json(
    model_name: str,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 4096,
    fallback_model: str | None = "deepseek",
) -> dict[str, Any]:
    """
    Call LLM and request JSON output format.
    Returns the same dict as call_llm.
    """
    return call_llm(
        model_name=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        fallback_model=fallback_model,
    )
