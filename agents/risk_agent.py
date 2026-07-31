"""
ContractIQ — Risk Analysis Agent

Analyzes extracted contract clauses to assess risk levels, scores,
potential impact, and suggested modifications using LLM structured output.
"""

import json
import logging
from typing import Any

from gateway.router import route_task

logger = logging.getLogger(__name__)

RISK_LEVELS = ["High", "Medium", "Low"]

RISK_ANALYSIS_PROMPT = """You are a legal risk analysis expert specializing in contract review.

Analyze the following contract text and its extracted clauses. For EACH clause provided,
assess the legal and business risk.

Contract text (first 8000 characters):
---
{text}
---

Extracted clauses:
{clauses_json}

For each clause, provide:
- "clause_type": the clause type (must match one of the provided clause types exactly)
- "risk_level": one of "High", "Medium", or "Low"
- "risk_score": a number from 0 to 100 (0 = no risk, 100 = maximum risk)
- "explanation": a concise explanation of why this risk level was assigned
- "impact": the potential legal or business impact if this clause is unfavorable
- "suggested_modification": a specific suggestion to reduce risk in this clause

Also provide aggregate risk metrics:
- "overall_risk_score": weighted average risk score across all clauses (0-100)
- "risk_level": overall risk level ("High" if score >= 70, "Medium" if >= 40, "Low" otherwise)
- "high_risk_count": number of High risk clauses
- "medium_risk_count": number of Medium risk clauses
- "low_risk_count": number of Low risk clauses

Return a JSON object with this exact structure:
{{
  "clause_risks": [
    {{
      "clause_type": "...",
      "risk_level": "High|Medium|Low",
      "risk_score": 0-100,
      "explanation": "...",
      "impact": "...",
      "suggested_modification": "..."
    }}
  ],
  "overall_risk_score": 0-100,
  "risk_level": "High|Medium|Low",
  "high_risk_count": 0,
  "medium_risk_count": 0,
  "low_risk_count": 0
}}

Return ONLY valid JSON. No markdown, no code fences, no extra text."""


def analyze_risks(cleaned_text: str, clauses: list[dict]) -> dict[str, Any]:
    """
    Analyze risk for each extracted clause and compute overall risk.

    Args:
        cleaned_text: Cleaned contract text
        clauses: List of extracted clause dicts (clause_type, text, confidence)

    Returns:
        dict with keys: clause_risks, overall_risk_score, risk_level,
                        high_risk_count, medium_risk_count, low_risk_count,
                        model, provider, tokens_in, tokens_out, latency_ms
    """
    # Truncate text for context window
    truncated = cleaned_text[:8000]

    # Build clause summary for the prompt
    clauses_summary = []
    for c in clauses:
        clauses_summary.append({
            "clause_type": c.get("clause_type", "Unknown"),
            "text": c.get("text", "")[:500],
        })

    prompt = RISK_ANALYSIS_PROMPT.format(
        text=truncated,
        clauses_json=json.dumps(clauses_summary, indent=2),
    )

    messages = [
        {"role": "system", "content": "You are a legal risk analysis AI. Always respond with valid JSON."},
        {"role": "user", "content": prompt},
    ]

    response = route_task(
        task="risk_analysis",
        messages=messages,
        temperature=0.1,
        max_tokens=4096,
    )

    # Parse response
    try:
        content = response["content"].strip()
        # Handle markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        # Validate and clean clause risks
        clause_risks = []
        clause_types_from_input = {c.get("clause_type") for c in clauses}

        for cr in result.get("clause_risks", []):
            clause_type = cr.get("clause_type", "")

            # Validate clause_type matches an input clause
            if clause_type not in clause_types_from_input:
                # Try fuzzy matching
                matched = False
                for ct in clause_types_from_input:
                    if ct.lower() in clause_type.lower() or clause_type.lower() in ct.lower():
                        clause_type = ct
                        matched = True
                        break
                if not matched:
                    continue

            # Validate risk_level
            risk_level = cr.get("risk_level", "Low")
            if risk_level not in RISK_LEVELS:
                risk_level = "Medium"

            # Validate risk_score
            risk_score = float(cr.get("risk_score", 50))
            risk_score = max(0.0, min(100.0, risk_score))

            clause_risks.append({
                "clause_type": clause_type,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "explanation": cr.get("explanation", ""),
                "impact": cr.get("impact", ""),
                "suggested_modification": cr.get("suggested_modification", ""),
            })

        # Compute aggregate metrics (validate or recompute from clause data)
        high_count = sum(1 for cr in clause_risks if cr["risk_level"] == "High")
        medium_count = sum(1 for cr in clause_risks if cr["risk_level"] == "Medium")
        low_count = sum(1 for cr in clause_risks if cr["risk_level"] == "Low")

        # Use LLM's overall score if present, otherwise compute weighted average
        overall_score = float(result.get("overall_risk_score", 0))
        if overall_score == 0 and clause_risks:
            overall_score = sum(cr["risk_score"] for cr in clause_risks) / len(clause_risks)
        overall_score = max(0.0, min(100.0, overall_score))

        # Determine overall risk level from score
        if overall_score >= 70:
            overall_level = "High"
        elif overall_score >= 40:
            overall_level = "Medium"
        else:
            overall_level = "Low"

        logger.info(
            f"Risk analysis complete: overall_score={overall_score:.1f}, "
            f"level={overall_level}, clauses_assessed={len(clause_risks)}"
        )

        return {
            "clause_risks": clause_risks,
            "overall_risk_score": overall_score,
            "risk_level": overall_level,
            "high_risk_count": high_count,
            "medium_risk_count": medium_count,
            "low_risk_count": low_count,
            "model": response["model"],
            "provider": response["provider"],
            "tokens_in": response["tokens_in"],
            "tokens_out": response["tokens_out"],
            "latency_ms": response["latency_ms"],
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse risk analysis response: {e}")
        return {
            "clause_risks": [],
            "overall_risk_score": 0,
            "risk_level": "Low",
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "model": response.get("model", "unknown"),
            "provider": response.get("provider", "unknown"),
            "tokens_in": response.get("tokens_in", 0),
            "tokens_out": response.get("tokens_out", 0),
            "latency_ms": response.get("latency_ms", 0),
        }
