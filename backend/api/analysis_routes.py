"""
ContractIQ — Analysis Routes

POST /analyze  — trigger full LangGraph workflow on a contract
POST /ask      — contract Q&A using RAG
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.connection import get_db
from backend.database.models import (
    Contract,
    Clause,
    RiskReport,
    AgentRun,
    ModelUsage,
    Approval,
    User,
)
from backend.schemas.contract import (
    ContractDetailResponse,
    ClauseResult,
    QARequest,
    QAResponse,
)
from backend.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Analysis"])


# ─────────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    contract_id: str


# ─────────────────────────────────────────────
# POST /analyze
# ─────────────────────────────────────────────
@router.post("/analyze", response_model=ContractDetailResponse)
async def analyze_contract(
    request: AnalyzeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the full LangGraph multi-agent workflow on a contract.

    Steps: parse → classify → extract_clauses → index_vectors →
           risk_analysis → compliance → summary → recommendation →
           human_review_decision
    """
    # Fetch contract
    result = await db.execute(
        select(Contract).where(
            Contract.id == request.contract_id,
            Contract.user_id == user.id,
        )
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if not contract.raw_text:
        raise HTTPException(status_code=422, detail="Contract has no extracted text")

    # Update status to processing
    contract.status = "processing"
    await db.flush()

    # Run the LangGraph workflow
    try:
        from graph.workflow import run_workflow

        final_state = run_workflow(
            contract_id=contract.id,
            raw_text=contract.raw_text,
            file_type=contract.file_type,
        )

    except Exception as e:
        logger.error(f"Workflow failed for contract {contract.id}: {e}")
        contract.status = "uploaded"  # Reset status
        raise HTTPException(
            status_code=500,
            detail=f"Analysis workflow failed: {str(e)}",
        )

    # ── Persist results to database ──

    # Update contract record
    contract.contract_type = final_state.get("contract_type")
    contract.classification_confidence = final_state.get("classification_confidence")
    contract.overall_risk_score = final_state.get("overall_risk_score", 0)
    contract.summary = final_state.get("summary")
    contract.recommendations = final_state.get("recommendations")
    contract.requires_human_review = final_state.get("requires_human_review", False)
    contract.processing_time_ms = final_state.get("total_processing_time_ms")
    contract.analyzed_at = datetime.utcnow()
    contract.status = "review_pending" if contract.requires_human_review else "analyzed"

    # Save extracted clauses
    for clause_data in final_state.get("clauses", []):
        clause = Clause(
            contract_id=contract.id,
            clause_type=clause_data.get("clause_type", "Unknown"),
            text=clause_data.get("text", ""),
            risk_level=clause_data.get("risk_level"),
            risk_score=clause_data.get("risk_score"),
            confidence=clause_data.get("confidence"),
            explanation=clause_data.get("explanation"),
            impact=clause_data.get("impact"),
            suggested_modification=clause_data.get("suggested_modification"),
        )
        db.add(clause)

    # Save risk report
    if final_state.get("overall_risk_score") is not None:
        risk_report = RiskReport(
            contract_id=contract.id,
            overall_score=final_state.get("overall_risk_score", 0),
            risk_breakdown={
                "high_risk_count": final_state.get("high_risk_count", 0),
                "medium_risk_count": final_state.get("medium_risk_count", 0),
                "low_risk_count": final_state.get("low_risk_count", 0),
                "risk_level": final_state.get("risk_level", "Low"),
            },
            summary=final_state.get("overall_assessment", ""),
            recommendations=final_state.get("recommendations"),
        )
        db.add(risk_report)

    # Save agent runs and model usage
    for run_data in final_state.get("agent_runs", []):
        agent_run = AgentRun(
            contract_id=contract.id,
            agent_name=run_data.get("agent_name", "unknown"),
            status=run_data.get("status", "completed"),
            duration_ms=run_data.get("latency_ms", 0),
            model_used=run_data.get("model", ""),
            output_data=None,
        )
        db.add(agent_run)
        await db.flush()

        # Save model usage if this agent used an LLM
        if run_data.get("model") and run_data.get("tokens_in", 0) > 0:
            usage = ModelUsage(
                agent_run_id=agent_run.id,
                model=run_data.get("model", ""),
                provider=run_data.get("provider", "unknown"),
                tokens_in=run_data.get("tokens_in", 0),
                tokens_out=run_data.get("tokens_out", 0),
                latency_ms=run_data.get("latency_ms", 0),
            )
            db.add(usage)

    # Create approval record if human review required or risk >= 70
    if contract.requires_human_review or (contract.overall_risk_score or 0) >= 70:
        approval = Approval(
            contract_id=contract.id,
            status="pending",
        )
        db.add(approval)

    # Audit log
    await log_action(
        db,
        action="analyze",
        user_id=user.id,
        resource_type="contract",
        resource_id=contract.id,
        details={
            "contract_type": contract.contract_type,
            "risk_score": contract.overall_risk_score,
            "clauses_found": final_state.get("total_clauses_found", 0),
            "processing_time_ms": contract.processing_time_ms,
            "requires_review": contract.requires_human_review,
        },
    )

    await db.flush()

    # Build response
    clause_result = await db.execute(
        select(Clause).where(Clause.contract_id == contract.id)
    )
    clauses = clause_result.scalars().all()

    clause_list = [
        ClauseResult(
            clause_type=c.clause_type,
            text=c.text,
            confidence=c.confidence or 0.0,
            risk_level=c.risk_level,
            risk_score=c.risk_score,
            explanation=c.explanation,
            impact=c.impact,
            suggested_modification=c.suggested_modification,
        )
        for c in clauses
    ]

    return ContractDetailResponse(
        id=contract.id,
        filename=contract.filename,
        file_type=contract.file_type,
        status=contract.status,
        contract_type=contract.contract_type,
        classification_confidence=contract.classification_confidence,
        overall_risk_score=contract.overall_risk_score,
        requires_human_review=contract.requires_human_review,
        uploaded_at=contract.uploaded_at,
        analyzed_at=contract.analyzed_at,
        processing_time_ms=contract.processing_time_ms,
        raw_text=contract.raw_text,
        summary=contract.summary,
        recommendations=contract.recommendations,
        clauses=clause_list,
    )


# ─────────────────────────────────────────────
# POST /ask
# ─────────────────────────────────────────────
@router.post("/ask", response_model=QAResponse)
async def ask_question(
    request: QARequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a natural language question about a specific contract.
    Uses RAG (ChromaDB retrieval + LLM) to answer.
    """
    # Verify contract exists and belongs to user
    result = await db.execute(
        select(Contract).where(
            Contract.id == request.contract_id,
            Contract.user_id == user.id,
        )
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.status == "uploaded":
        raise HTTPException(
            status_code=422,
            detail="Contract must be analyzed before asking questions. Run /analyze first.",
        )

    # Run Q&A via retrieval agent
    try:
        from agents.retrieval_agent import answer_question

        qa_result = answer_question(request.contract_id, request.question)

    except Exception as e:
        logger.error(f"Q&A failed for contract {request.contract_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Q&A processing failed: {str(e)}",
        )

    # Audit log
    await log_action(
        db,
        action="ask_question",
        user_id=user.id,
        resource_type="contract",
        resource_id=request.contract_id,
        details={
            "question": request.question,
            "confidence": qa_result.get("confidence", 0),
        },
    )

    return QAResponse(
        answer=qa_result["answer"],
        evidence=qa_result.get("evidence", []),
        clause_references=qa_result.get("clause_references", []),
        confidence=qa_result.get("confidence", 0.5),
    )
