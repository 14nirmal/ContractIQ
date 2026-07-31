"""
ContractIQ — Comparison Routes (Phase 4)

Compare two contracts side-by-side: clause diffs, risk deltas, and summary.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.connection import get_db
from backend.database.models import Contract, Clause, User

router = APIRouter(prefix="/api", tags=["Comparison"])


# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────
class CompareRequest(BaseModel):
    contract_a_id: str
    contract_b_id: str


class ClauseDiff(BaseModel):
    clause_type: str
    change_type: str  # added, removed, modified, unchanged
    text_a: str | None = None
    text_b: str | None = None
    risk_a: float | None = None
    risk_b: float | None = None
    risk_impact: str = "unchanged"  # increased, decreased, unchanged


class CompareResponse(BaseModel):
    contract_a: dict
    contract_b: dict
    clause_diffs: list[ClauseDiff] = Field(default_factory=list)
    risk_score_a: float | None = None
    risk_score_b: float | None = None
    risk_delta: float = 0.0
    summary: str = ""
    total_added: int = 0
    total_removed: int = 0
    total_modified: int = 0
    total_unchanged: int = 0


# ─────────────────────────────────────────────
# POST /api/compare
# ─────────────────────────────────────────────
@router.post("/compare", response_model=CompareResponse)
async def compare_contracts(
    request: CompareRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare two contracts and return clause-level diffs."""
    # Fetch both contracts
    result_a = await db.execute(
        select(Contract).where(Contract.id == request.contract_a_id, Contract.user_id == user.id)
    )
    contract_a = result_a.scalar_one_or_none()

    result_b = await db.execute(
        select(Contract).where(Contract.id == request.contract_b_id, Contract.user_id == user.id)
    )
    contract_b = result_b.scalar_one_or_none()

    if not contract_a or not contract_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both contracts not found",
        )

    # Fetch clauses for both
    clauses_a_result = await db.execute(
        select(Clause).where(Clause.contract_id == request.contract_a_id)
    )
    clauses_a = {c.clause_type: c for c in clauses_a_result.scalars().all()}

    clauses_b_result = await db.execute(
        select(Clause).where(Clause.contract_id == request.contract_b_id)
    )
    clauses_b = {c.clause_type: c for c in clauses_b_result.scalars().all()}

    # Compute diffs
    all_clause_types = set(clauses_a.keys()) | set(clauses_b.keys())
    diffs = []
    added = removed = modified = unchanged = 0

    for ct in sorted(all_clause_types):
        a = clauses_a.get(ct)
        b = clauses_b.get(ct)

        if a and not b:
            diffs.append(ClauseDiff(
                clause_type=ct,
                change_type="removed",
                text_a=a.text,
                risk_a=a.risk_score,
                risk_impact="decreased" if (a.risk_score or 0) > 50 else "unchanged",
            ))
            removed += 1
        elif b and not a:
            diffs.append(ClauseDiff(
                clause_type=ct,
                change_type="added",
                text_b=b.text,
                risk_b=b.risk_score,
                risk_impact="increased" if (b.risk_score or 0) > 50 else "unchanged",
            ))
            added += 1
        elif a and b:
            # Check if text differs
            text_changed = a.text.strip() != b.text.strip()
            risk_a = a.risk_score or 0
            risk_b = b.risk_score or 0

            if risk_b > risk_a + 10:
                impact = "increased"
            elif risk_a > risk_b + 10:
                impact = "decreased"
            else:
                impact = "unchanged"

            change_type = "modified" if text_changed else "unchanged"
            if change_type == "modified":
                modified += 1
            else:
                unchanged += 1

            diffs.append(ClauseDiff(
                clause_type=ct,
                change_type=change_type,
                text_a=a.text,
                text_b=b.text,
                risk_a=risk_a,
                risk_b=risk_b,
                risk_impact=impact,
            ))

    # Compute risk delta
    risk_a = contract_a.overall_risk_score or 0
    risk_b = contract_b.overall_risk_score or 0
    risk_delta = risk_b - risk_a

    # Generate summary
    parts = []
    if added:
        parts.append(f"{added} clause(s) added")
    if removed:
        parts.append(f"{removed} clause(s) removed")
    if modified:
        parts.append(f"{modified} clause(s) modified")
    if unchanged:
        parts.append(f"{unchanged} clause(s) unchanged")

    if risk_delta > 0:
        parts.append(f"overall risk increased by {risk_delta:.1f} points")
    elif risk_delta < 0:
        parts.append(f"overall risk decreased by {abs(risk_delta):.1f} points")
    else:
        parts.append("overall risk unchanged")

    summary = f"Comparison of '{contract_a.filename}' vs '{contract_b.filename}': " + ", ".join(parts) + "."

    return CompareResponse(
        contract_a={"id": contract_a.id, "filename": contract_a.filename, "contract_type": contract_a.contract_type},
        contract_b={"id": contract_b.id, "filename": contract_b.filename, "contract_type": contract_b.contract_type},
        clause_diffs=diffs,
        risk_score_a=risk_a,
        risk_score_b=risk_b,
        risk_delta=risk_delta,
        summary=summary,
        total_added=added,
        total_removed=removed,
        total_modified=modified,
        total_unchanged=unchanged,
    )
