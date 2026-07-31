"""
ContractIQ — LangGraph Workflow

Assembles the multi-agent StateGraph and provides the run_workflow entry point.
"""

import logging
import time
from typing import Any

from langgraph.graph import StateGraph, END

from graph.state import ContractState
from graph.nodes import (
    parse_node,
    classify_node,
    extract_clauses_node,
    vector_store_node,
    risk_analysis_node,
    compliance_node,
    summary_node,
    recommendation_node,
    human_review_decision_node,
)
from graph.edges import should_continue_after_parse

logger = logging.getLogger(__name__)


def build_workflow() -> StateGraph:
    """
    Build the ContractIQ multi-agent workflow graph.

    Pipeline:
        parse → classify → extract_clauses → vector_store →
        risk_analysis → compliance → generate_summary → recommendation →
        human_review_decision → END
    """
    workflow = StateGraph(ContractState)

    # ── Add Nodes ──
    workflow.add_node("parse", parse_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("extract_clauses", extract_clauses_node)
    workflow.add_node("vector_store", vector_store_node)
    workflow.add_node("risk_analysis", risk_analysis_node)
    workflow.add_node("compliance", compliance_node)
    workflow.add_node("generate_summary", summary_node)
    workflow.add_node("recommendation", recommendation_node)
    workflow.add_node("human_review_decision", human_review_decision_node)

    # ── Set Entry Point ──
    workflow.set_entry_point("parse")

    # ── Add Edges ──
    # Parse → conditional (check if text was extracted)
    workflow.add_conditional_edges(
        "parse",
        should_continue_after_parse,
        {
            "classify": "classify",
            "end": END,
        },
    )

    # Sequential flow
    workflow.add_edge("classify", "extract_clauses")
    workflow.add_edge("extract_clauses", "vector_store")
    workflow.add_edge("vector_store", "risk_analysis")
    workflow.add_edge("risk_analysis", "compliance")
    workflow.add_edge("compliance", "generate_summary")
    workflow.add_edge("generate_summary", "recommendation")
    workflow.add_edge("recommendation", "human_review_decision")
    workflow.add_edge("human_review_decision", END)

    return workflow


# ── Compile the workflow ──
_compiled_workflow = None


def get_compiled_workflow():
    """Get or compile the workflow graph (cached)."""
    global _compiled_workflow
    if _compiled_workflow is None:
        workflow = build_workflow()
        _compiled_workflow = workflow.compile()
        logger.info("✅ LangGraph workflow compiled successfully")
    return _compiled_workflow


def run_workflow(contract_id: str, raw_text: str, file_type: str = "pdf") -> dict[str, Any]:
    """
    Execute the full contract analysis workflow.

    Args:
        contract_id: Contract identifier
        raw_text: Raw extracted text from the document
        file_type: File type (pdf, docx, txt)

    Returns:
        Final state dict with all analysis results
    """
    start_time = time.time()

    logger.info(f"🚀 Starting workflow for contract {contract_id}")

    # Initial state
    initial_state = ContractState(
        contract_id=contract_id,
        raw_text=raw_text,
        file_type=file_type,
        errors=[],
        agent_runs=[],
    )

    # Run the graph
    compiled = get_compiled_workflow()
    final_state = compiled.invoke(initial_state)

    # Calculate total processing time
    total_ms = int((time.time() - start_time) * 1000)
    final_state["total_processing_time_ms"] = total_ms

    # Log summary
    agent_count = len(final_state.get("agent_runs", []))
    error_count = len(final_state.get("errors", []))
    logger.info(
        f"✅ Workflow complete for {contract_id}: "
        f"type={final_state.get('contract_type', 'Unknown')}, "
        f"clauses={final_state.get('total_clauses_found', 0)}, "
        f"risk={final_state.get('overall_risk_score', 0)}, "
        f"agents={agent_count}, errors={error_count}, "
        f"time={total_ms}ms"
    )

    return dict(final_state)
