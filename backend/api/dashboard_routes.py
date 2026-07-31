"""
ContractIQ — Dashboard Routes

Aggregated analytics and statistics for the dashboard.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.connection import get_db
from backend.database.models import Contract, Approval, AgentRun, ModelUsage, User
from backend.schemas.contract import DashboardStats, ContractResponse

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated dashboard statistics for the current user."""

    # Total contracts
    total_result = await db.execute(
        select(func.count()).where(Contract.user_id == user.id)
    )
    total_contracts = total_result.scalar() or 0

    # Analyzed contracts
    analyzed_result = await db.execute(
        select(func.count()).where(
            Contract.user_id == user.id,
            Contract.status.in_(["analyzed", "approved", "rejected", "review_pending"]),
        )
    )
    contracts_analyzed = analyzed_result.scalar() or 0

    # Average risk score
    avg_risk_result = await db.execute(
        select(func.avg(Contract.overall_risk_score)).where(
            Contract.user_id == user.id,
            Contract.overall_risk_score.isnot(None),
        )
    )
    average_risk_score = round(avg_risk_result.scalar() or 0.0, 1)

    # High-risk contracts (score > 70)
    high_risk_result = await db.execute(
        select(func.count()).where(
            Contract.user_id == user.id,
            Contract.overall_risk_score > 70,
        )
    )
    high_risk_contracts = high_risk_result.scalar() or 0

    # Pending reviews
    pending_result = await db.execute(
        select(func.count()).select_from(Approval).join(Contract).where(
            Contract.user_id == user.id,
            Approval.status == "pending",
        )
    )
    pending_reviews = pending_result.scalar() or 0

    # Average processing time
    avg_time_result = await db.execute(
        select(func.avg(Contract.processing_time_ms)).where(
            Contract.user_id == user.id,
            Contract.processing_time_ms.isnot(None),
        )
    )
    avg_processing_time = round(avg_time_result.scalar() or 0.0, 0)

    # Total tokens used
    tokens_result = await db.execute(
        select(func.sum(ModelUsage.tokens_in + ModelUsage.tokens_out))
        .select_from(ModelUsage)
        .join(AgentRun)
        .join(Contract)
        .where(Contract.user_id == user.id)
    )
    total_tokens = tokens_result.scalar() or 0

    # Risk distribution
    risk_dist_result = await db.execute(
        select(
            case(
                (Contract.overall_risk_score > 70, "high"),
                (Contract.overall_risk_score > 40, "medium"),
                else_="low",
            ).label("risk_category"),
            func.count().label("count"),
        )
        .where(
            Contract.user_id == user.id,
            Contract.overall_risk_score.isnot(None),
        )
        .group_by("risk_category")
    )
    risk_distribution = {row.risk_category: row.count for row in risk_dist_result}

    # Contract type distribution
    type_dist_result = await db.execute(
        select(
            Contract.contract_type,
            func.count().label("count"),
        )
        .where(
            Contract.user_id == user.id,
            Contract.contract_type.isnot(None),
        )
        .group_by(Contract.contract_type)
    )
    contract_type_distribution = {row.contract_type: row.count for row in type_dist_result}

    # Recent uploads (last 10)
    recent_result = await db.execute(
        select(Contract)
        .where(Contract.user_id == user.id)
        .order_by(desc(Contract.uploaded_at))
        .limit(10)
    )
    recent_contracts = recent_result.scalars().all()

    # Model usage breakdown
    model_result = await db.execute(
        select(
            ModelUsage.model,
            func.count().label("calls"),
            func.sum(ModelUsage.tokens_in + ModelUsage.tokens_out).label("total_tokens"),
        )
        .select_from(ModelUsage)
        .join(AgentRun)
        .join(Contract)
        .where(Contract.user_id == user.id)
        .group_by(ModelUsage.model)
    )
    model_usage = {
        row.model: {"calls": row.calls, "tokens": row.total_tokens or 0}
        for row in model_result
    }

    return DashboardStats(
        total_contracts=total_contracts,
        contracts_analyzed=contracts_analyzed,
        average_risk_score=average_risk_score,
        high_risk_contracts=high_risk_contracts,
        pending_reviews=pending_reviews,
        avg_processing_time_ms=avg_processing_time,
        total_tokens_used=total_tokens,
        risk_distribution=risk_distribution,
        contract_type_distribution=contract_type_distribution,
        recent_uploads=[ContractResponse.model_validate(c) for c in recent_contracts],
        model_usage=model_usage,
    )
