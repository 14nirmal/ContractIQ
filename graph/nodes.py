"""
ContractIQ — LangGraph Node Functions

Each node wraps an agent call, updates the shared state, and records execution metadata.
"""

import logging
import time
from typing import Any

from graph.state import ContractState, AgentRunRecord

logger = logging.getLogger(__name__)


def _record_run(
    agent_name: str,
    status: str,
    start_time: float,
    model: str = "",
    provider: str = "",
    tokens_in: int = 0,
    tokens_out: int = 0,
    error: str | None = None,
) -> AgentRunRecord:
    """Create an agent run record."""
    latency = int((time.time() - start_time) * 1000)
    return AgentRunRecord(
        agent_name=agent_name,
        status=status,
        model=model,
        provider=provider,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency,
        error=error,
    )


# ─────────────────────────────────────────────
# Node 1: Parse Document
# ─────────────────────────────────────────────
def parse_node(state: ContractState) -> dict[str, Any]:
    """Parse and clean the raw contract text."""
    from agents.parser_agent import parse_contract

    start = time.time()
    logger.info(f"[parse_node] Processing contract {state.get('contract_id', 'unknown')}")

    try:
        result = parse_contract(state["raw_text"])

        run = _record_run("parser", "completed", start)

        return {
            "cleaned_text": result["cleaned_text"],
            "sections": result["sections"],
            "char_count": result["char_count"],
            "section_count": result["section_count"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }

    except Exception as e:
        logger.error(f"[parse_node] Failed: {e}")
        run = _record_run("parser", "failed", start, error=str(e))
        return {
            "cleaned_text": state.get("raw_text", ""),
            "sections": [],
            "char_count": 0,
            "section_count": 0,
            "errors": state.get("errors", []) + [f"Parser failed: {str(e)}"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }


# ─────────────────────────────────────────────
# Node 2: Classify Contract
# ─────────────────────────────────────────────
def classify_node(state: ContractState) -> dict[str, Any]:
    """Classify the contract type."""
    from agents.classification_agent import classify_contract

    start = time.time()
    logger.info(f"[classify_node] Classifying contract {state.get('contract_id', 'unknown')}")

    try:
        result = classify_contract(state["cleaned_text"])

        run = _record_run(
            "classification", "completed", start,
            model=result.get("model", ""),
            provider=result.get("provider", ""),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
        )

        return {
            "contract_type": result["contract_type"],
            "classification_confidence": result["confidence"],
            "classification_reasoning": result.get("reasoning", ""),
            "agent_runs": state.get("agent_runs", []) + [run],
        }

    except Exception as e:
        logger.error(f"[classify_node] Failed: {e}")
        run = _record_run("classification", "failed", start, error=str(e))
        return {
            "contract_type": "Unknown",
            "classification_confidence": 0.0,
            "classification_reasoning": f"Classification failed: {str(e)}",
            "errors": state.get("errors", []) + [f"Classification failed: {str(e)}"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }


# ─────────────────────────────────────────────
# Node 3: Extract Clauses
# ─────────────────────────────────────────────
def extract_clauses_node(state: ContractState) -> dict[str, Any]:
    """Extract legal clauses from the contract."""
    from agents.clause_agent import extract_clauses

    start = time.time()
    logger.info(f"[extract_clauses_node] Extracting clauses from {state.get('contract_id', 'unknown')}")

    try:
        result = extract_clauses(state["cleaned_text"])

        run = _record_run(
            "clause_extraction", "completed", start,
            model=result.get("model", ""),
            provider=result.get("provider", ""),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
        )

        return {
            "clauses": result["clauses"],
            "total_clauses_found": result["total_clauses_found"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }

    except Exception as e:
        logger.error(f"[extract_clauses_node] Failed: {e}")
        run = _record_run("clause_extraction", "failed", start, error=str(e))
        return {
            "clauses": [],
            "total_clauses_found": 0,
            "errors": state.get("errors", []) + [f"Clause extraction failed: {str(e)}"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }


# ─────────────────────────────────────────────
# Node 4: Index in Vector Store
# ─────────────────────────────────────────────
def vector_store_node(state: ContractState) -> dict[str, Any]:
    """Index contract chunks into ChromaDB."""
    from agents.retrieval_agent import index_contract

    start = time.time()
    contract_id = state.get("contract_id", "unknown")
    logger.info(f"[vector_store_node] Indexing {contract_id}")

    try:
        result = index_contract(contract_id, state["cleaned_text"])

        run = _record_run("vector_store", "completed", start)

        return {
            "chunks_indexed": result["chunks_indexed"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }

    except Exception as e:
        logger.error(f"[vector_store_node] Failed: {e}")
        run = _record_run("vector_store", "failed", start, error=str(e))
        return {
            "chunks_indexed": 0,
            "errors": state.get("errors", []) + [f"Vector indexing failed: {str(e)}"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }


# ─────────────────────────────────────────────
# Node 5: Risk Analysis
# ─────────────────────────────────────────────
def risk_analysis_node(state: ContractState) -> dict[str, Any]:
    """Analyze risk for each extracted clause."""
    start = time.time()
    logger.info(f"[risk_analysis_node] Analyzing risks for {state.get('contract_id', 'unknown')}")

    try:
        from agents.risk_agent import analyze_risks
        result = analyze_risks(state["cleaned_text"], state.get("clauses", []))

        run = _record_run(
            "risk_analysis", "completed", start,
            model=result.get("model", ""),
            provider=result.get("provider", ""),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
        )

        # Update clauses with risk data
        updated_clauses = state.get("clauses", [])
        for clause_risk in result.get("clause_risks", []):
            for clause in updated_clauses:
                if clause.get("clause_type") == clause_risk.get("clause_type"):
                    clause["risk_level"] = clause_risk.get("risk_level")
                    clause["risk_score"] = clause_risk.get("risk_score")
                    clause["explanation"] = clause_risk.get("explanation")
                    clause["impact"] = clause_risk.get("impact")
                    clause["suggested_modification"] = clause_risk.get("suggested_modification")

        return {
            "clauses": updated_clauses,
            "overall_risk_score": result.get("overall_risk_score", 0),
            "risk_level": result.get("risk_level", "Low"),
            "high_risk_count": result.get("high_risk_count", 0),
            "medium_risk_count": result.get("medium_risk_count", 0),
            "low_risk_count": result.get("low_risk_count", 0),
            "agent_runs": state.get("agent_runs", []) + [run],
        }

    except Exception as e:
        logger.error(f"[risk_analysis_node] Failed: {e}")
        run = _record_run("risk_analysis", "failed", start, error=str(e))
        return {
            "overall_risk_score": 0,
            "risk_level": "Low",
            "errors": state.get("errors", []) + [f"Risk analysis failed: {str(e)}"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }


# ─────────────────────────────────────────────
# Node 6: Compliance Check
# ─────────────────────────────────────────────
def compliance_node(state: ContractState) -> dict[str, Any]:
    """Check contract compliance."""
    start = time.time()
    logger.info(f"[compliance_node] Checking compliance for {state.get('contract_id', 'unknown')}")

    try:
        from agents.compliance_agent import check_compliance
        result = check_compliance(
            state["cleaned_text"],
            state.get("contract_type", "Unknown"),
            state.get("clauses", []),
        )

        run = _record_run(
            "compliance", "completed", start,
            model=result.get("model", ""),
            provider=result.get("provider", ""),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
        )

        return {
            "is_compliant": result.get("is_compliant", True),
            "compliance_score": result.get("score", 100),
            "compliance_issues": result.get("issues", []),
            "missing_clauses": result.get("missing_clauses", []),
            "agent_runs": state.get("agent_runs", []) + [run],
        }

    except Exception as e:
        logger.error(f"[compliance_node] Failed: {e}")
        run = _record_run("compliance", "failed", start, error=str(e))
        return {
            "is_compliant": True,
            "compliance_score": 0,
            "errors": state.get("errors", []) + [f"Compliance check failed: {str(e)}"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }


# ─────────────────────────────────────────────
# Node 7: Summary
# ─────────────────────────────────────────────
def summary_node(state: ContractState) -> dict[str, Any]:
    """Generate contract summary."""
    start = time.time()
    logger.info(f"[summary_node] Summarizing {state.get('contract_id', 'unknown')}")

    try:
        from agents.summary_agent import generate_summary
        result = generate_summary(
            state["cleaned_text"],
            state.get("contract_type", "Unknown"),
            state.get("clauses", []),
        )

        run = _record_run(
            "summary", "completed", start,
            model=result.get("model", ""),
            provider=result.get("provider", ""),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
        )

        return {
            "summary": result.get("summary", {}),
            "agent_runs": state.get("agent_runs", []) + [run],
        }

    except Exception as e:
        logger.error(f"[summary_node] Failed: {e}")
        run = _record_run("summary", "failed", start, error=str(e))
        return {
            "summary": {},
            "errors": state.get("errors", []) + [f"Summary failed: {str(e)}"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }


# ─────────────────────────────────────────────
# Node 8: Recommendations
# ─────────────────────────────────────────────
def recommendation_node(state: ContractState) -> dict[str, Any]:
    """Generate recommendations based on analysis."""
    start = time.time()
    logger.info(f"[recommendation_node] Generating recommendations for {state.get('contract_id', 'unknown')}")

    try:
        from agents.recommendation_agent import generate_recommendations
        result = generate_recommendations(
            state.get("contract_type", "Unknown"),
            state.get("clauses", []),
            state.get("overall_risk_score", 0),
            state.get("compliance_issues", []),
        )

        run = _record_run(
            "recommendation", "completed", start,
            model=result.get("model", ""),
            provider=result.get("provider", ""),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
        )

        return {
            "recommendations": result.get("recommendations", []),
            "overall_assessment": result.get("overall_assessment", ""),
            "agent_runs": state.get("agent_runs", []) + [run],
        }

    except Exception as e:
        logger.error(f"[recommendation_node] Failed: {e}")
        run = _record_run("recommendation", "failed", start, error=str(e))
        return {
            "recommendations": [],
            "overall_assessment": "",
            "errors": state.get("errors", []) + [f"Recommendations failed: {str(e)}"],
            "agent_runs": state.get("agent_runs", []) + [run],
        }


# ─────────────────────────────────────────────
# Node 9: Human Review Decision
# ─────────────────────────────────────────────
def human_review_decision_node(state: ContractState) -> dict[str, Any]:
    """Determine if human review is required based on risk score."""
    risk_score = state.get("overall_risk_score", 0)
    requires_review = risk_score > 85

    logger.info(
        f"[human_review_decision_node] Risk={risk_score}, "
        f"requires_review={requires_review}"
    )

    return {
        "requires_human_review": requires_review,
    }
