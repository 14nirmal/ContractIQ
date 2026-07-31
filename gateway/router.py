"""
ContractIQ — AI Gateway Router

Maps tasks to optimal models based on task type.
Provides a high-level interface for the agents to call the right model.
"""

import logging
from typing import Any

from gateway.litellm_gateway import call_llm, call_llm_json

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Task-to-Model Routing Table
# ─────────────────────────────────────────────
TASK_ROUTING = {
    "classification": {"primary": "gemini", "fallback": "deepseek"},
    "clause_extraction": {"primary": "gemini", "fallback": "deepseek"},
    "summary": {"primary": "gemini", "fallback": "deepseek"},
    "risk_analysis": {"primary": "qwen", "fallback": "gemini"},
    "compliance": {"primary": "gemini", "fallback": "deepseek"},
    "recommendation": {"primary": "gemini", "fallback": "deepseek"},
    "long_reasoning": {"primary": "llama", "fallback": "gemini"},
    "qa": {"primary": "gemini", "fallback": "deepseek"},
    "comparison": {"primary": "gemini", "fallback": "deepseek"},
}


def route_task(
    task: str,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 4096,
    json_mode: bool = True,
) -> dict[str, Any]:
    """
    Route a task to the appropriate model based on the routing table.

    Args:
        task: Task name (classification, clause_extraction, summary, etc.)
        messages: Chat messages in OpenAI format
        temperature: Sampling temperature
        max_tokens: Maximum output tokens
        json_mode: Whether to request JSON output

    Returns:
        dict with keys: content, model, provider, tokens_in, tokens_out, latency_ms
    """
    routing = TASK_ROUTING.get(task)
    if not routing:
        logger.warning(f"Unknown task '{task}', defaulting to gemini")
        routing = {"primary": "gemini", "fallback": "deepseek"}

    primary = routing["primary"]
    fallback = routing["fallback"]

    logger.info(f"Routing task '{task}' to model '{primary}' (fallback: '{fallback}')")

    call_fn = call_llm_json if json_mode else call_llm

    return call_fn(
        model_name=primary,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        fallback_model=fallback,
    )


def get_model_for_task(task: str) -> str:
    """Get the primary model name for a task."""
    routing = TASK_ROUTING.get(task, {"primary": "gemini"})
    return routing["primary"]
