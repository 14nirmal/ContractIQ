"""
ContractIQ — LangGraph State Definition

TypedDict defining the shared state that flows through the multi-agent graph.
"""

from typing import Any, TypedDict


class AgentRunRecord(TypedDict, total=False):
    """Record of a single agent execution."""
    agent_name: str
    status: str  # running, completed, failed
    model: str
    provider: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    error: str | None


class ClauseData(TypedDict, total=False):
    """Extracted clause data."""
    clause_type: str
    text: str
    confidence: float
    risk_level: str | None
    risk_score: float | None
    explanation: str | None
    impact: str | None
    suggested_modification: str | None


class ContractState(TypedDict, total=False):
    """
    Shared state for the ContractIQ LangGraph workflow.

    Each agent node reads from and writes to this state.
    The state flows through the graph sequentially.
    """
    # ── Input ──
    contract_id: str
    raw_text: str
    file_type: str

    # ── Parser Agent ──
    cleaned_text: str
    sections: list[dict[str, Any]]
    char_count: int
    section_count: int

    # ── Classification Agent ──
    contract_type: str
    classification_confidence: float
    classification_reasoning: str

    # ── Clause Extraction Agent ──
    clauses: list[ClauseData]
    total_clauses_found: int

    # ── Vector Store Agent ──
    chunks_indexed: int

    # ── Risk Analysis Agent ──
    overall_risk_score: float
    risk_level: str  # High, Medium, Low
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int

    # ── Compliance Agent ──
    is_compliant: bool
    compliance_score: float
    compliance_issues: list[dict[str, Any]]
    missing_clauses: list[str]

    # ── Summary Agent ──
    summary: dict[str, Any]

    # ── Recommendation Agent ──
    recommendations: list[dict[str, Any]]
    overall_assessment: str

    # ── Human Review ──
    requires_human_review: bool
    human_decision: str | None  # approved, rejected, revision_requested

    # ── Workflow Metadata ──
    errors: list[str]
    agent_runs: list[AgentRunRecord]
    total_processing_time_ms: int
