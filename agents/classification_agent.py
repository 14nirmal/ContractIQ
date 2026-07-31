"""
ContractIQ — Classification Agent

Classifies contracts into one of 8 types using LLM structured output.
"""

import json
import logging
from typing import Any

from gateway.router import route_task

logger = logging.getLogger(__name__)

CONTRACT_TYPES = [
    "NDA",
    "Employment",
    "Lease",
    "Vendor",
    "Service",
    "Partnership",
    "Licensing",
    "Consulting",
]

CLASSIFICATION_PROMPT = """You are a legal contract classification expert.

Analyze the following contract text and classify it into exactly ONE of these types:
{types}

Return your answer as a JSON object with these exact fields:
- "contract_type": one of the types listed above
- "confidence": a float between 0.0 and 1.0 indicating your confidence
- "reasoning": a brief explanation of why you chose this classification

Contract text (first 3000 characters):
---
{text}
---

Return ONLY valid JSON. No markdown, no code fences, no extra text."""


def classify_contract(text: str) -> dict[str, Any]:
    """
    Classify a contract into one of the predefined types.

    Args:
        text: Cleaned contract text

    Returns:
        dict with keys: contract_type, confidence, reasoning,
                        model, provider, tokens_in, tokens_out, latency_ms
    """
    # Truncate to first 3000 chars for classification (sufficient for type detection)
    truncated = text[:3000]

    prompt = CLASSIFICATION_PROMPT.format(
        types=", ".join(CONTRACT_TYPES),
        text=truncated,
    )

    messages = [
        {"role": "system", "content": "You are a legal contract analysis AI. Always respond with valid JSON."},
        {"role": "user", "content": prompt},
    ]

    response = route_task(
        task="classification",
        messages=messages,
        temperature=0.1,
        max_tokens=256,
    )

    # Parse JSON response
    try:
        content = response["content"].strip()
        # Handle markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        # Validate contract_type
        contract_type = result.get("contract_type", "Unknown")
        if contract_type not in CONTRACT_TYPES:
            # Try fuzzy matching
            for ct in CONTRACT_TYPES:
                if ct.lower() in contract_type.lower():
                    contract_type = ct
                    break
            else:
                contract_type = "Service"  # Default fallback

        confidence = float(result.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        return {
            "contract_type": contract_type,
            "confidence": confidence,
            "reasoning": result.get("reasoning", ""),
            "model": response["model"],
            "provider": response["provider"],
            "tokens_in": response["tokens_in"],
            "tokens_out": response["tokens_out"],
            "latency_ms": response["latency_ms"],
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse classification response: {e}")
        return {
            "contract_type": "Service",
            "confidence": 0.3,
            "reasoning": f"Classification parsing failed: {str(e)}",
            "model": response.get("model", "unknown"),
            "provider": response.get("provider", "unknown"),
            "tokens_in": response.get("tokens_in", 0),
            "tokens_out": response.get("tokens_out", 0),
            "latency_ms": response.get("latency_ms", 0),
        }
