"""
ContractIQ — Compliance Check Agent

Evaluates contract compliance against standard legal requirements
based on the contract type, identifying missing clauses and issues.
"""

import json
import logging
from typing import Any

from gateway.router import route_task

logger = logging.getLogger(__name__)

# Mandatory clauses by contract type — used in the prompt for type-specific evaluation
MANDATORY_CLAUSES_BY_TYPE = {
    "NDA": ["Confidentiality", "Non-solicitation", "Termination", "Governing Law"],
    "Employment": ["Payment", "Termination", "Non-compete", "Confidentiality", "Governing Law"],
    "Lease": ["Payment", "Termination", "Renewal", "Liability", "Governing Law"],
    "Vendor": ["Payment", "Termination", "Liability", "Warranty", "Indemnification", "Governing Law"],
    "Service": ["Payment", "Termination", "Liability", "Warranty", "Governing Law"],
    "Partnership": ["Payment", "Termination", "Liability", "Arbitration", "Governing Law"],
    "Licensing": ["Payment", "Termination", "Intellectual Property", "Liability", "Governing Law"],
    "Consulting": ["Payment", "Termination", "Confidentiality", "Intellectual Property", "Governing Law"],
}

COMPLIANCE_PROMPT = """You are a legal compliance expert specializing in contract review.

Analyze the following {contract_type} contract for compliance with standard legal requirements.

Contract text (first 8000 characters):
---
{text}
---

Extracted clauses found in this contract:
{clauses_json}

Mandatory clauses for a {contract_type} contract:
{mandatory_clauses}

Evaluate the contract for:
1. Whether all mandatory clauses for this contract type are present
2. Whether existing clauses meet standard legal requirements
3. Any compliance gaps, ambiguities, or problematic language

Return a JSON object with this exact structure:
{{
  "is_compliant": true/false,
  "score": 0-100,
  "issues": [
    {{
      "issue_type": "missing_clause|ambiguous_language|non_standard_terms|regulatory_gap|unfair_terms",
      "description": "Clear description of the compliance issue",
      "severity": "High|Medium|Low",
      "affected_clause": "clause type affected, or null if general",
      "recommendation": "Specific action to resolve this issue"
    }}
  ],
  "missing_clauses": ["list of mandatory clause types that are missing"]
}}

A contract is compliant (is_compliant=true) if the score is >= 70 and there are no High severity issues.

Return ONLY valid JSON. No markdown, no code fences, no extra text."""


def check_compliance(
    cleaned_text: str,
    contract_type: str,
    clauses: list[dict],
) -> dict[str, Any]:
    """
    Check contract compliance against standard legal requirements.

    Args:
        cleaned_text: Cleaned contract text
        contract_type: Classified contract type (NDA, Employment, etc.)
        clauses: List of extracted clause dicts

    Returns:
        dict with keys: is_compliant, score, issues, missing_clauses,
                        model, provider, tokens_in, tokens_out, latency_ms
    """
    truncated = cleaned_text[:8000]

    # Build clause summary
    clauses_summary = []
    found_clause_types = set()
    for c in clauses:
        ct = c.get("clause_type", "Unknown")
        found_clause_types.add(ct)
        clauses_summary.append({
            "clause_type": ct,
            "text": c.get("text", "")[:500],
        })

    # Get mandatory clauses for this contract type
    mandatory = MANDATORY_CLAUSES_BY_TYPE.get(contract_type, ["Governing Law", "Termination"])
    mandatory_str = ", ".join(mandatory)

    prompt = COMPLIANCE_PROMPT.format(
        contract_type=contract_type,
        text=truncated,
        clauses_json=json.dumps(clauses_summary, indent=2),
        mandatory_clauses=mandatory_str,
    )

    messages = [
        {"role": "system", "content": "You are a legal compliance analysis AI. Always respond with valid JSON."},
        {"role": "user", "content": prompt},
    ]

    response = route_task(
        task="compliance",
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

        # Validate and clean issues
        issues = []
        valid_severities = {"High", "Medium", "Low"}
        for issue in result.get("issues", []):
            severity = issue.get("severity", "Medium")
            if severity not in valid_severities:
                severity = "Medium"

            issues.append({
                "issue_type": issue.get("issue_type", "regulatory_gap"),
                "description": issue.get("description", ""),
                "severity": severity,
                "affected_clause": issue.get("affected_clause"),
                "recommendation": issue.get("recommendation", ""),
            })

        # Validate missing clauses
        missing_clauses = result.get("missing_clauses", [])
        if not isinstance(missing_clauses, list):
            missing_clauses = []

        # Cross-check: add any mandatory clauses not found in extracted clauses
        for mc in mandatory:
            if mc not in found_clause_types and mc not in missing_clauses:
                missing_clauses.append(mc)

        # Validate score
        score = float(result.get("score", 50))
        score = max(0.0, min(100.0, score))

        # Determine compliance
        has_high_severity = any(i["severity"] == "High" for i in issues)
        is_compliant = result.get("is_compliant", score >= 70 and not has_high_severity)
        if isinstance(is_compliant, str):
            is_compliant = is_compliant.lower() == "true"

        logger.info(
            f"Compliance check complete: score={score:.1f}, "
            f"compliant={is_compliant}, issues={len(issues)}, "
            f"missing={len(missing_clauses)}"
        )

        return {
            "is_compliant": is_compliant,
            "score": score,
            "issues": issues,
            "missing_clauses": missing_clauses,
            "model": response["model"],
            "provider": response["provider"],
            "tokens_in": response["tokens_in"],
            "tokens_out": response["tokens_out"],
            "latency_ms": response["latency_ms"],
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse compliance response: {e}")
        # Compute basic missing clauses from extracted data
        basic_missing = [mc for mc in mandatory if mc not in found_clause_types]
        return {
            "is_compliant": len(basic_missing) == 0,
            "score": max(0, 100 - len(basic_missing) * 15),
            "issues": [],
            "missing_clauses": basic_missing,
            "model": response.get("model", "unknown"),
            "provider": response.get("provider", "unknown"),
            "tokens_in": response.get("tokens_in", 0),
            "tokens_out": response.get("tokens_out", 0),
            "latency_ms": response.get("latency_ms", 0),
        }
