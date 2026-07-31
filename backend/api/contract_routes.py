"""
ContractIQ — Contract Routes

CRUD endpoints for contract management.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.connection import get_db
from backend.database.models import Contract, Clause, User, AuditLog
from backend.schemas.contract import (
    ContractResponse,
    ContractDetailResponse,
    ContractListResponse,
    ClauseResult,
)
from backend.services.file_handler import save_upload, delete_file
from backend.services.ocr_pipeline import extract_text
from backend.services.audit import log_action

router = APIRouter(prefix="/api", tags=["Contracts"])


@router.post("/upload", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def upload_contract(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a contract file (PDF, DOCX, TXT) and extract text."""
    # Save file to disk
    file_path, file_type = await save_upload(file, user.id)

    # Extract text using OCR pipeline
    try:
        raw_text = extract_text(file_path, file_type)
    except Exception as e:
        # Clean up file on extraction failure
        delete_file(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text from file: {str(e)}",
        )

    if not raw_text:
        delete_file(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text could be extracted from the uploaded file",
        )

    # Create contract record
    contract = Contract(
        user_id=user.id,
        filename=file.filename,
        file_type=file_type,
        file_path=file_path,
        raw_text=raw_text,
        status="uploaded",
    )
    db.add(contract)
    await db.flush()

    # Audit log
    await log_action(
        db,
        action="upload",
        user_id=user.id,
        resource_type="contract",
        resource_id=contract.id,
        details={"filename": file.filename, "file_type": file_type, "text_length": len(raw_text)},
    )

    return ContractResponse.model_validate(contract)


@router.get("/contracts", response_model=ContractListResponse)
async def list_contracts(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all contracts for the current user with pagination."""
    query = select(Contract).where(Contract.user_id == user.id)

    if status_filter:
        query = query.where(Contract.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(desc(Contract.uploaded_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    contracts = result.scalars().all()

    return ContractListResponse(
        contracts=[ContractResponse.model_validate(c) for c in contracts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/contract/{contract_id}", response_model=ContractDetailResponse)
async def get_contract(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full contract details including clauses."""
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

    # Fetch clauses
    clause_result = await db.execute(
        select(Clause).where(Clause.contract_id == contract_id)
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


@router.delete("/contract/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a contract and its associated file."""
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

    # Delete file from disk
    delete_file(contract.file_path)

    # Delete from database (cascades to clauses, reports, etc.)
    await db.delete(contract)

    # Audit log
    await log_action(
        db,
        action="delete",
        user_id=user.id,
        resource_type="contract",
        resource_id=contract_id,
        details={"filename": contract.filename},
    )
