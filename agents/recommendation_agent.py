"""
ContractIQ — Recommendation Agent

Synthesizes findings from risk analysis and compliance checks
to generate prioritized, actionable recommendations.
"""

import json
import logging
from typing import Any

from gateway.router import route_task

logger = logging.getLogger(__name__)

RECOMMENDATION_PROMPT = """You are a senior legal advisor specializing in contract negotiations.

Based on the following analysis of a {contract_type} contract, generate prioritized,
actionable recommendations.

Overall risk score: {risk_score}/100

Extracted clauses with risk assessments:
{clauses_json}

Compliance issues found:
{compliance_json}

Generate recommendations that:
1. Address the highest-risk clauses first
2. Cover compliance gaps and missing clauses
3. Provide specific, actionable language changes or additions
4. Consider the contract type and industry best practices

Return a JSON object with this exact structure:
{{
  "recommendations": [
    {{
      "category": "risk|compliance|general",
      "priority": "High|Medium|Low",
      "description": "Specific, actionable recommendation with suggested language if applicable",
      "related_clause": "The clause type this relates to, or null if general"
    }}
  ],
  "overall_assessment": "A 2-3 sentence strategic assessment: should the reviewing party sign as-is, negotiate specific terms, or reject the contract? Include key reasoning."
}}

Order recommendations by priority (High first, then Medium, then Low).
Provide between 3 and 10 recommendations.

Return ONLY valid JSON. No markdown, no code fences, no extra text."""


def generate_recommendations(
    contract_type: str,
    clauses: list[dict],
    overall_risk_score: float,
    compliance_issues: list,
) -> dict[str, Any]:
    """
    Generate prioritized recommendations based on risk and compliance analysis.

    Args:
        contract_type: Classified contract type
        clauses: List of clause dicts (with risk data if available)
        overall_risk_score: Overall risk score (0-100)
        compliance_issues: List of compliance issue dicts

    Returns:
        dict with keys: recommendations, overall_assessment,
                        model, provider, tokens_in, tokens_out, latency_ms
    """
    # Build clause summary with risk data
    clauses_summary = []
    for c in clauses:
        clause_info = {
            "clause_type": c.get("clause_type", "Unknown"),
            "text": c.get("text", "")[:300],
            "risk_level": c.get("risk_level", "N/A"),
            "risk_score": c.get("risk_score", "N/A"),
        }
        if c.get("explanation"):
            clause_info["risk_explanation"] = c["explanation"][:200]
        if c.get("suggested_modification"):
            clause_info["existing_suggestion"] = c["suggested_modification"][:200]
        clauses_summary.append(clause_info)

    # Build compliance issues summary
    compliance_summary = []
    if compliance_issues:
        for issue in compliance_issues:
            if isinstance(issue, dict):
                compliance_summary.append({
                    "issue_type": issue.get("issue_type", "unknown"),
                    "description": issue.get("description", "")[:200],
                    "severity": issue.get("severity", "Medium"),
                    "affected_clause": issue.get("affected_clause"),
                })
            elif isinstance(issue, str):
                compliance_summary.append({"description": issue})

    if not compliance_summary:
        compliance_summary = [{"description": "No compliance issues detected."}]

    prompt = RECOMMENDATION_PROMPT.format(
        contract_type=contract_type,
        risk_score=overall_risk_score,
        clauses_json=json.dumps(clauses_summary, indent=2),
        compliance_json=json.dumps(compliance_summary, indent=2),
    )

    messages = [
        {"role": "system", "content": "You are a senior legal advisory AI. Always respond with valid JSON."},
        {"role": "user", "content": prompt},
    ]

    response = route_task(
        task="recommendation",
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

        # Validate and clean recommendations
        recommendations = []
        valid_categories = {"risk", "compliance", "general"}
        valid_priorities = {"High", "Medium", "Low"}

        for rec in result.get("recommendations", []):
            category = rec.get("category", "general")
            if category not in valid_categories:
                category = "general"

            priority = rec.get("priority", "Medium")
            if priority not in valid_priorities:
                priority = "Medium"

            description = rec.get("description", "")
            if not description:
                continue

            recommendations.append({
                "category": category,
                "priority": priority,
                "description": description,
                "related_clause": rec.get("related_clause"),
            })

        # Sort by priority: High > Medium > Low
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 1))

        overall_assessment = result.get("overall_assessment", "")
        if not overall_assessment:
            # Generate a basic assessment from risk score
            if overall_risk_score >= 70:
                overall_assessment = (
                    f"This {contract_type} contract carries significant risk (score: {overall_risk_score:.0f}/100). "
                    "Major revisions are recommended before signing. Key areas of concern should be renegotiated."
                )
            elif overall_risk_score >= 40:
                overall_assessment = (
                    f"This {contract_type} contract has moderate risk (score: {overall_risk_score:.0f}/100). "
                    "Several clauses should be reviewed and potentially modified before signing."
                )
            else:
                overall_assessment = (
                    f"This {contract_type} contract is relatively low risk (score: {overall_risk_score:.0f}/100). "
                    "Minor improvements are suggested but the contract is generally acceptable."
                )

        logger.info(
            f"Recommendations generated: {len(recommendations)} items, "
            f"high_priority={sum(1 for r in recommendations if r['priority'] == 'High')}"
        )

        return {
            "recommendations": recommendations,
            "overall_assessment": overall_assessment,
            "model": response["model"],
            "provider": response["provider"],
            "tokens_in": response["tokens_in"],
            "tokens_out": response["tokens_out"],
            "latency_ms": response["latency_ms"],
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse recommendation response: {e}")
        return {
            "recommendations": [],
            "overall_assessment": f"Recommendation generation failed: {str(e)}",
            "model": response.get("model", "unknown"),
            "provider": response.get("provider", "unknown"),
            "tokens_in": response.get("tokens_in", 0),
            "tokens_out": response.get("tokens_out", 0),
            "latency_ms": response.get("latency_ms", 0),
        }
