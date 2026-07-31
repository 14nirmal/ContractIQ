"""
ContractIQ — Review Routes (Phase 4)

Human-in-the-loop review queue and decision endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.connection import get_db
from backend.database.models import Contract, Clause, Approval, User
from backend.schemas.contract import ContractResponse, ClauseResult
from backend.services.audit import log_action

router = APIRouter(prefix="/api/review", tags=["Review"])


# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────
class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="approved, rejected, or revision_requested")
    notes: str | None = Field(None, description="Reviewer notes")


class ReviewContractResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    contract_type: str | None
    overall_risk_score: float | None
    requires_human_review: bool
    uploaded_at: datetime
    analyzed_at: datetime | None
    clauses: list[ClauseResult] = Field(default_factory=list)
    summary: dict | None = None
    recommendations: list | None = None
    review_status: str | None = None
    review_notes: str | None = None

    model_config = {"from_attributes": True}


class ReviewQueueResponse(BaseModel):
    contracts: list[ReviewContractResponse]
    total: int


# ─────────────────────────────────────────────
# GET /api/review/queue
# ─────────────────────────────────────────────
@router.get("/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch all contracts flagged for human review."""
    query = select(Contract).where(
        Contract.user_id == user.id,
        Contract.status.in_(["analyzed", "review_pending"]),
        or_(
            Contract.requires_human_review == True,
            Contract.overall_risk_score > 70,
        ),
    ).order_by(Contract.overall_risk_score.desc())

    result = await db.execute(query)
    contracts = result.scalars().all()

    items = []
    for c in contracts:
        # Fetch clauses
        clause_result = await db.execute(
            select(Clause).where(Clause.contract_id == c.id)
        )
        clauses = clause_result.scalars().all()

        # Fetch latest approval
        approval_result = await db.execute(
            select(Approval)
            .where(Approval.contract_id == c.id)
            .order_by(Approval.created_at.desc())
            .limit(1)
        )
        approval = approval_result.scalar_one_or_none()

        clause_list = [
            ClauseResult(
                clause_type=cl.clause_type,
                text=cl.text,
                confidence=cl.confidence or 0.0,
                risk_level=cl.risk_level,
                risk_score=cl.risk_score,
                explanation=cl.explanation,
                impact=cl.impact,
                suggested_modification=cl.suggested_modification,
            )
            for cl in clauses
        ]

        items.append(ReviewContractResponse(
            id=c.id,
            filename=c.filename,
            file_type=c.file_type,
            status=c.status,
            contract_type=c.contract_type,
            overall_risk_score=c.overall_risk_score,
            requires_human_review=c.requires_human_review,
            uploaded_at=c.uploaded_at,
            analyzed_at=c.analyzed_at,
            clauses=clause_list,
            summary=c.summary,
            recommendations=c.recommendations,
            review_status=approval.status if approval else "pending",
            review_notes=approval.notes if approval else None,
        ))

    return ReviewQueueResponse(contracts=items, total=len(items))


# ─────────────────────────────────────────────
# POST /api/review/{contract_id}/decision
# ─────────────────────────────────────────────
@router.post("/{contract_id}/decision")
async def submit_review_decision(
    contract_id: str,
    request: ReviewDecisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a reviewer's decision on a contract."""
    valid_decisions = {"approved", "rejected", "revision_requested"}
    if request.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision. Must be one of: {valid_decisions}",
        )

    # Verify contract exists and belongs to user
    result = await db.execute(
        select(Contract).where(
            Contract.id == contract_id,
            Contract.user_id == user.id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )

    # Create approval record
    approval = Approval(
        contract_id=contract_id,
        reviewer_id=user.id,
        status=request.decision,
        notes=request.notes,
        decided_at=datetime.utcnow(),
    )
    db.add(approval)

    # Update contract status
    contract.status = request.decision

    # Audit log
    await log_action(
        db,
        action=f"review_{request.decision}",
        user_id=user.id,
        resource_type="contract",
        resource_id=contract_id,
        details={"decision": request.decision, "notes": request.notes},
    )

    return {
        "message": f"Contract {request.decision} successfully",
        "contract_id": contract_id,
        "decision": request.decision,
    }
