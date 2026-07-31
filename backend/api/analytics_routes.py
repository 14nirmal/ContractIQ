"""
ContractIQ — Analytics Routes (Phase 4)

Agent metrics, token usage, risk trends, and audit log endpoints.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.connection import get_db
from backend.database.models import (
    Contract, AgentRun, ModelUsage, AuditLog, User,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ─────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────
class AgentMetric(BaseModel):
    agent_name: str
    total_runs: int = 0
    avg_duration_ms: float = 0.0
    success_rate: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0


class ProviderMetric(BaseModel):
    provider: str
    model: str
    total_calls: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0


class AuditEntry(BaseModel):
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None
    timestamp: str


class AnalyticsMetricsResponse(BaseModel):
    agent_metrics: list[AgentMetric] = Field(default_factory=list)
    provider_metrics: list[ProviderMetric] = Field(default_factory=list)
    total_contracts: int = 0
    total_analyzed: int = 0
    total_tokens_used: int = 0


class RiskTrend(BaseModel):
    contract_type: str
    count: int = 0
    avg_risk_score: float = 0.0


class AnalyticsTrendsResponse(BaseModel):
    risk_distribution: dict = Field(default_factory=dict)
    contract_type_breakdown: list[RiskTrend] = Field(default_factory=list)
    audit_logs: list[AuditEntry] = Field(default_factory=list)


# ─────────────────────────────────────────────
# GET /api/analytics/metrics
# ─────────────────────────────────────────────
@router.get("/metrics", response_model=AnalyticsMetricsResponse)
async def get_analytics_metrics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agent execution metrics and provider usage stats."""
    # Get user's contract IDs
    contract_ids_query = select(Contract.id).where(Contract.user_id == user.id)
    contract_ids_result = await db.execute(contract_ids_query)
    contract_ids = [r[0] for r in contract_ids_result.all()]

    if not contract_ids:
        return AnalyticsMetricsResponse()

    # Agent metrics
    agent_query = (
        select(
            AgentRun.agent_name,
            func.count(AgentRun.id).label("total_runs"),
            func.avg(AgentRun.duration_ms).label("avg_duration"),
            func.sum(case((AgentRun.status == "completed", 1), else_=0)).label("success_count"),
        )
        .where(AgentRun.contract_id.in_(contract_ids))
        .group_by(AgentRun.agent_name)
    )
    agent_result = await db.execute(agent_query)
    agent_metrics = []
    for row in agent_result.all():
        total = row.total_runs or 1
        agent_metrics.append(AgentMetric(
            agent_name=row.agent_name,
            total_runs=row.total_runs,
            avg_duration_ms=float(row.avg_duration or 0),
            success_rate=round((row.success_count or 0) / total * 100, 1),
        ))

    # Provider / model metrics
    provider_query = (
        select(
            ModelUsage.provider,
            ModelUsage.model,
            func.count(ModelUsage.id).label("total_calls"),
            func.sum(ModelUsage.tokens_in + ModelUsage.tokens_out).label("total_tokens"),
            func.avg(ModelUsage.latency_ms).label("avg_latency"),
        )
        .join(AgentRun, ModelUsage.agent_run_id == AgentRun.id)
        .where(AgentRun.contract_id.in_(contract_ids))
        .group_by(ModelUsage.provider, ModelUsage.model)
    )
    provider_result = await db.execute(provider_query)
    provider_metrics = []
    total_tokens = 0
    for row in provider_result.all():
        tokens = int(row.total_tokens or 0)
        total_tokens += tokens
        provider_metrics.append(ProviderMetric(
            provider=row.provider,
            model=row.model,
            total_calls=row.total_calls,
            total_tokens=tokens,
            avg_latency_ms=float(row.avg_latency or 0),
        ))

    # Contract counts
    total_contracts = len(contract_ids)
    analyzed_result = await db.execute(
        select(func.count()).select_from(Contract).where(
            Contract.id.in_(contract_ids),
            Contract.status.in_(["analyzed", "approved", "rejected", "review_pending"]),
        )
    )
    total_analyzed = analyzed_result.scalar() or 0

    return AnalyticsMetricsResponse(
        agent_metrics=agent_metrics,
        provider_metrics=provider_metrics,
        total_contracts=total_contracts,
        total_analyzed=total_analyzed,
        total_tokens_used=total_tokens,
    )


# ─────────────────────────────────────────────
# GET /api/analytics/trends
# ─────────────────────────────────────────────
@router.get("/trends", response_model=AnalyticsTrendsResponse)
async def get_analytics_trends(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get risk distribution trends, contract type breakdown, and audit logs."""
    # Risk distribution (High / Medium / Low)
    risk_query = (
        select(
            case(
                (Contract.overall_risk_score >= 70, "High"),
                (Contract.overall_risk_score >= 40, "Medium"),
                else_="Low",
            ).label("risk_tier"),
            func.count(Contract.id).label("count"),
        )
        .where(
            Contract.user_id == user.id,
            Contract.overall_risk_score.isnot(None),
        )
        .group_by("risk_tier")
    )
    risk_result = await db.execute(risk_query)
    risk_distribution = {row.risk_tier: row.count for row in risk_result.all()}

    # Contract type breakdown with avg risk
    type_query = (
        select(
            Contract.contract_type,
            func.count(Contract.id).label("count"),
            func.avg(Contract.overall_risk_score).label("avg_risk"),
        )
        .where(
            Contract.user_id == user.id,
            Contract.contract_type.isnot(None),
        )
        .group_by(Contract.contract_type)
    )
    type_result = await db.execute(type_query)
    type_breakdown = [
        RiskTrend(
            contract_type=row.contract_type,
            count=row.count,
            avg_risk_score=round(float(row.avg_risk or 0), 1),
        )
        for row in type_result.all()
    ]

    # Audit logs (most recent)
    audit_query = (
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
    )
    audit_result = await db.execute(audit_query)
    audit_logs = [
        AuditEntry(
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            timestamp=log.timestamp.isoformat() if log.timestamp else "",
        )
        for log in audit_result.scalars().all()
    ]

    return AnalyticsTrendsResponse(
        risk_distribution=risk_distribution,
        contract_type_breakdown=type_breakdown,
        audit_logs=audit_logs,
    )
