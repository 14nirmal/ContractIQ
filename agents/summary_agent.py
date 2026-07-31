"""
ContractIQ — Summary Agent

Generates a structured executive summary of a contract including
key obligations, dates, financial terms, and high-risk areas.
"""

import json
import logging
from typing import Any

from gateway.router import route_task

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """You are a legal contract summarization expert.

Analyze the following {contract_type} contract and generate a comprehensive summary.

Contract text:
---
{text}
---

Extracted clauses:
{clauses_json}

Generate a structured summary with the following sections:
- "executive_summary": A concise 2-3 paragraph overview of the contract covering parties, purpose, key terms, and notable provisions
- "key_obligations": List of key obligations for each party (strings)
- "important_dates": List of important dates, deadlines, or time-bound provisions mentioned (strings)
- "financial_terms": List of all financial terms, payment amounts, fees, or monetary provisions (strings)
- "responsibilities": List of key responsibilities assigned to each party (strings)
- "termination_conditions": List of conditions under which the contract can be terminated (strings)
- "high_risk_clauses": List of clauses that carry elevated legal or business risk (strings)
- "recommendations": List of brief recommendations for the reviewing party (strings)

Return a JSON object with this exact structure:
{{
  "summary": {{
    "executive_summary": "...",
    "key_obligations": ["..."],
    "important_dates": ["..."],
    "financial_terms": ["..."],
    "responsibilities": ["..."],
    "termination_conditions": ["..."],
    "high_risk_clauses": ["..."],
    "recommendations": ["..."]
  }}
}}

If a section has no relevant content, return an empty array for that field.
Return ONLY valid JSON. No markdown, no code fences, no extra text."""


def generate_summary(
    cleaned_text: str,
    contract_type: str,
    clauses: list[dict],
) -> dict[str, Any]:
    """
    Generate a structured executive summary of the contract.

    Args:
        cleaned_text: Cleaned contract text
        contract_type: Classified contract type
        clauses: List of extracted clause dicts

    Returns:
        dict with keys: summary (nested dict),
                        model, provider, tokens_in, tokens_out, latency_ms
    """
    # Use more text for summarization — up to 10000 chars
    truncated = cleaned_text[:10000]

    # Build clause summary
    clauses_summary = []
    for c in clauses:
        clauses_summary.append({
            "clause_type": c.get("clause_type", "Unknown"),
            "text": c.get("text", "")[:500],
            "risk_level": c.get("risk_level", "N/A"),
        })

    prompt = SUMMARY_PROMPT.format(
        contract_type=contract_type,
        text=truncated,
        clauses_json=json.dumps(clauses_summary, indent=2),
    )

    messages = [
        {"role": "system", "content": "You are a legal contract summarization AI. Always respond with valid JSON."},
        {"role": "user", "content": prompt},
    ]

    response = route_task(
        task="summary",
        messages=messages,
        temperature=0.2,
        max_tokens=4096,
    )

    # Parse response
    try:
        content = response["content"].strip()
        # Handle markdown code fences
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        # Extract the summary object
        summary = result.get("summary", result)  # Handle both nested and flat structures

        # Ensure all expected keys exist with proper types
        validated_summary = {
            "executive_summary": summary.get("executive_summary", "Summary not available."),
            "key_obligations": _ensure_string_list(summary.get("key_obligations", [])),
            "important_dates": _ensure_string_list(summary.get("important_dates", [])),
            "financial_terms": _ensure_string_list(summary.get("financial_terms", [])),
            "responsibilities": _ensure_string_list(summary.get("responsibilities", [])),
            "termination_conditions": _ensure_string_list(summary.get("termination_conditions", [])),
            "high_risk_clauses": _ensure_string_list(summary.get("high_risk_clauses", [])),
            "recommendations": _ensure_string_list(summary.get("recommendations", [])),
        }

        logger.info(
            f"Summary generated: {len(validated_summary['executive_summary'])} chars, "
            f"obligations={len(validated_summary['key_obligations'])}, "
            f"financial_terms={len(validated_summary['financial_terms'])}"
        )

        return {
            "summary": validated_summary,
            "model": response["model"],
            "provider": response["provider"],
            "tokens_in": response["tokens_in"],
            "tokens_out": response["tokens_out"],
            "latency_ms": response["latency_ms"],
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse summary response: {e}")
        return {
            "summary": {
                "executive_summary": "Summary generation failed due to a parsing error.",
                "key_obligations": [],
                "important_dates": [],
                "financial_terms": [],
                "responsibilities": [],
                "termination_conditions": [],
                "high_risk_clauses": [],
                "recommendations": [],
            },
            "model": response.get("model", "unknown"),
            "provider": response.get("provider", "unknown"),
            "tokens_in": response.get("tokens_in", 0),
            "tokens_out": response.get("tokens_out", 0),
            "latency_ms": response.get("latency_ms", 0),
        }


def _ensure_string_list(value: Any) -> list[str]:
    """Ensure a value is a list of strings."""
    if not isinstance(value, list):
        return [str(value)] if value else []
    return [str(item) for item in value]
