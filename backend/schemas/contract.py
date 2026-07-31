"""
ContractIQ — Contract & Analysis Schemas

Pydantic models for contracts, clauses, risk analysis, and all agent outputs.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Classification
# ─────────────────────────────────────────────
class ClassificationResult(BaseModel):
    """Output from the classification agent."""
    contract_type: str = Field(..., description="One of: NDA, Employment, Lease, Vendor, Service, Partnership, Licensing, Consulting")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")


# ─────────────────────────────────────────────
# Clauses
# ─────────────────────────────────────────────
class ClauseResult(BaseModel):
    """A single extracted clause."""
    clause_type: str = Field(..., description="Type of clause")
    text: str = Field(..., description="Clause text extracted from contract")
    confidence: float = Field(..., ge=0, le=1, description="Extraction confidence 0-1")
    risk_level: str | None = Field(None, description="High, Medium, or Low")
    risk_score: float | None = Field(None, ge=0, le=100)
    explanation: str | None = Field(None, description="Why this clause is risky")
    impact: str | None = Field(None, description="Potential impact of this clause")
    suggested_modification: str | None = Field(None, description="Suggested change")


class ClauseExtractionResult(BaseModel):
    """Output from the clause extraction agent."""
    clauses: list[ClauseResult] = Field(default_factory=list)
    total_clauses_found: int = 0


# ─────────────────────────────────────────────
# Risk Analysis
# ─────────────────────────────────────────────
class RiskResult(BaseModel):
    """Risk analysis for a single clause."""
    clause_type: str
    risk_level: str = Field(..., description="High, Medium, or Low")
    risk_score: float = Field(..., ge=0, le=100)
    explanation: str
    impact: str
    suggested_modification: str


class RiskAnalysisResult(BaseModel):
    """Output from the risk analysis agent."""
    overall_risk_score: float = Field(..., ge=0, le=100)
    risk_level: str  # High, Medium, Low
    clause_risks: list[RiskResult] = Field(default_factory=list)
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0


# ─────────────────────────────────────────────
# Contract Summary
# ─────────────────────────────────────────────
class ContractSummary(BaseModel):
    """Output from the summary agent."""
    executive_summary: str
    key_obligations: list[str] = Field(default_factory=list)
    important_dates: list[str] = Field(default_factory=list)
    financial_terms: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    termination_conditions: list[str] = Field(default_factory=list)
    high_risk_clauses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────
# Q&A
# ─────────────────────────────────────────────
class QARequest(BaseModel):
    """Input for contract Q&A."""
    contract_id: str
    question: str


class QAResponse(BaseModel):
    """Output from the Q&A system."""
    answer: str
    evidence: list[str] = Field(default_factory=list, description="Supporting text from contract")
    clause_references: list[str] = Field(default_factory=list, description="Relevant clause types")
    confidence: float = Field(..., ge=0, le=1)


# ─────────────────────────────────────────────
# Compliance
# ─────────────────────────────────────────────
class ComplianceIssue(BaseModel):
    """A single compliance issue found."""
    issue_type: str
    description: str
    severity: str  # High, Medium, Low
    affected_clause: str | None = None
    recommendation: str


class ComplianceResult(BaseModel):
    """Output from the compliance check agent."""
    is_compliant: bool
    issues: list[ComplianceIssue] = Field(default_factory=list)
    missing_clauses: list[str] = Field(default_factory=list)
    score: float = Field(..., ge=0, le=100)


# ─────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────
class Recommendation(BaseModel):
    """A single recommendation."""
    category: str  # risk, compliance, general
    priority: str  # High, Medium, Low
    description: str
    related_clause: str | None = None


class RecommendationResult(BaseModel):
    """Output from the recommendation agent."""
    recommendations: list[Recommendation] = Field(default_factory=list)
    overall_assessment: str


# ─────────────────────────────────────────────
# Contract Comparison
# ─────────────────────────────────────────────
class ClauseChange(BaseModel):
    """A detected change between contract versions."""
    clause_type: str
    change_type: str  # added, removed, modified
    version_a_text: str | None = None
    version_b_text: str | None = None
    risk_impact: str  # increased, decreased, unchanged
    description: str


class ComparisonResult(BaseModel):
    """Output from contract comparison."""
    contract_a_id: str
    contract_b_id: str
    changes: list[ClauseChange] = Field(default_factory=list)
    risk_score_change: float
    summary: str


# ─────────────────────────────────────────────
# Contract API Responses
# ─────────────────────────────────────────────
class ContractResponse(BaseModel):
    """Contract data for API responses."""
    id: str
    filename: str
    file_type: str
    status: str
    contract_type: str | None
    classification_confidence: float | None
    overall_risk_score: float | None
    requires_human_review: bool
    uploaded_at: datetime
    analyzed_at: datetime | None
    processing_time_ms: int | None

    model_config = {"from_attributes": True}


class ContractDetailResponse(ContractResponse):
    """Full contract details including clauses and summary."""
    raw_text: str | None
    summary: dict | None
    recommendations: list | None
    clauses: list[ClauseResult] = Field(default_factory=list)


class ContractListResponse(BaseModel):
    """Paginated list of contracts."""
    contracts: list[ContractResponse]
    total: int
    page: int
    page_size: int


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────
class DashboardStats(BaseModel):
    """Aggregated dashboard statistics."""
    total_contracts: int = 0
    contracts_analyzed: int = 0
    average_risk_score: float = 0.0
    high_risk_contracts: int = 0
    pending_reviews: int = 0
    avg_processing_time_ms: float = 0.0
    total_tokens_used: int = 0
    risk_distribution: dict = Field(default_factory=dict)
    contract_type_distribution: dict = Field(default_factory=dict)
    recent_uploads: list[ContractResponse] = Field(default_factory=list)
    model_usage: dict = Field(default_factory=dict)

    model_config = {"protected_namespaces": ()}
