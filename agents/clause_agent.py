"""
ContractIQ — Clause Extraction Agent

Extracts 13 types of legal clauses from contract text using LLM.
"""

import json
import logging
from typing import Any

from gateway.router import route_task

logger = logging.getLogger(__name__)

CLAUSE_TYPES = [
    "Confidentiality",
    "Payment",
    "Termination",
    "Renewal",
    "Liability",
    "Warranty",
    "Arbitration",
    "Governing Law",
    "Intellectual Property",
    "Non-compete",
    "Non-solicitation",
    "Indemnification",
    "Force Majeure",
]

EXTRACTION_PROMPT = """You are a legal clause extraction expert.

Analyze the following contract text and extract all clauses that match these types:
{types}

For each clause found, return:
- "clause_type": one of the types listed above
- "text": the exact text of the clause from the contract (keep it concise, max 500 chars)
- "confidence": a float between 0.0 and 1.0

Return a JSON object with a single key "clauses" containing an array of clause objects.
If a clause type is not found in the contract, do not include it.

Example format:
{{
  "clauses": [
    {{
      "clause_type": "Confidentiality",
      "text": "Both parties agree to keep all shared information confidential...",
      "confidence": 0.95
    }}
  ]
}}

Contract text:
---
{text}
---

Return ONLY valid JSON. No markdown, no code fences, no extra text."""


def extract_clauses(text: str) -> dict[str, Any]:
    """
    Extract legal clauses from contract text.

    Args:
        text: Cleaned contract text

    Returns:
        dict with keys: clauses (list), total_clauses_found,
                        model, provider, tokens_in, tokens_out, latency_ms
    """
    # Use more of the text for extraction (up to 8000 chars)
    truncated = text[:8000]

    prompt = EXTRACTION_PROMPT.format(
        types=", ".join(CLAUSE_TYPES),
        text=truncated,
    )

    messages = [
        {"role": "system", "content": "You are a legal contract analysis AI. Always respond with valid JSON."},
        {"role": "user", "content": prompt},
    ]

    response = route_task(
        task="clause_extraction",
        messages=messages,
        temperature=0.1,
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
        raw_clauses = result.get("clauses", [])

        # Validate and clean clauses
        clauses = []
        for clause in raw_clauses:
            clause_type = clause.get("clause_type", "")
            # Validate clause type
            if clause_type not in CLAUSE_TYPES:
                # Try fuzzy matching
                matched = False
                for ct in CLAUSE_TYPES:
                    if ct.lower() in clause_type.lower() or clause_type.lower() in ct.lower():
                        clause_type = ct
                        matched = True
                        break
                if not matched:
                    continue

            confidence = float(clause.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            text_content = clause.get("text", "").strip()
            if not text_content:
                continue

            clauses.append({
                "clause_type": clause_type,
                "text": text_content[:1000],  # Cap length
                "confidence": confidence,
            })

        logger.info(f"Extracted {len(clauses)} clauses from contract")

        return {
            "clauses": clauses,
            "total_clauses_found": len(clauses),
            "model": response["model"],
            "provider": response["provider"],
            "tokens_in": response["tokens_in"],
            "tokens_out": response["tokens_out"],
            "latency_ms": response["latency_ms"],
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse clause extraction response: {e}")
        return {
            "clauses": [],
            "total_clauses_found": 0,
            "model": response.get("model", "unknown"),
            "provider": response.get("provider", "unknown"),
            "tokens_in": response.get("tokens_in", 0),
            "tokens_out": response.get("tokens_out", 0),
            "latency_ms": response.get("latency_ms", 0),
        }
