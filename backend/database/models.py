"""
ContractIQ — Database ORM Models

All 10 tables for the application.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from backend.database.connection import Base


def generate_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    contracts = relationship("Contract", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


# ─────────────────────────────────────────────
# Contracts
# ─────────────────────────────────────────────
class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx, txt
    file_path = Column(String(1000), nullable=False)
    raw_text = Column(Text, nullable=True)
    status = Column(String(50), default="uploaded")  # uploaded, processing, analyzed, review_pending, approved, rejected
    contract_type = Column(String(100), nullable=True)  # NDA, Employment, etc.
    classification_confidence = Column(Float, nullable=True)
    overall_risk_score = Column(Float, nullable=True)
    summary = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    requires_human_review = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, server_default=func.now())
    analyzed_at = Column(DateTime, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="contracts")
    clauses = relationship("Clause", back_populates="contract", cascade="all, delete-orphan")
    versions = relationship("ContractVersion", back_populates="contract", cascade="all, delete-orphan")
    risk_reports = relationship("RiskReport", back_populates="contract", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="contract", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="contract", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Contract Versions (for comparison)
# ─────────────────────────────────────────────
class ContractVersion(Base):
    __tablename__ = "contract_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    contract_id = Column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    raw_text = Column(Text, nullable=True)
    changes_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    contract = relationship("Contract", back_populates="versions")


# ─────────────────────────────────────────────
# Clauses
# ─────────────────────────────────────────────
class Clause(Base):
    __tablename__ = "clauses"

    id = Column(String, primary_key=True, default=generate_uuid)
    contract_id = Column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    clause_type = Column(String(100), nullable=False)  # Confidentiality, Payment, etc.
    text = Column(Text, nullable=False)
    risk_level = Column(String(20), nullable=True)  # High, Medium, Low
    risk_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    impact = Column(Text, nullable=True)
    suggested_modification = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    contract = relationship("Contract", back_populates="clauses")


# ─────────────────────────────────────────────
# Embeddings (tracking what's stored in ChromaDB)
# ─────────────────────────────────────────────
class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(String, primary_key=True, default=generate_uuid)
    contract_id = Column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# ─────────────────────────────────────────────
# Risk Reports
# ─────────────────────────────────────────────
class RiskReport(Base):
    __tablename__ = "risk_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    contract_id = Column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float, nullable=False)
    risk_breakdown = Column(JSON, nullable=True)  # Per-clause risk details
    summary = Column(Text, nullable=True)
    recommendations = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    contract = relationship("Contract", back_populates="risk_reports")


# ─────────────────────────────────────────────
# Approvals (Human-in-the-Loop)
# ─────────────────────────────────────────────
class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True, default=generate_uuid)
    contract_id = Column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String(50), default="pending")  # pending, approved, rejected, revision_requested
    notes = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    contract = relationship("Contract", back_populates="approvals")


# ─────────────────────────────────────────────
# Agent Runs (tracking each agent execution)
# ─────────────────────────────────────────────
class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    contract_id = Column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(50), default="running")  # running, completed, failed
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    contract = relationship("Contract", back_populates="agent_runs")
    model_usage = relationship("ModelUsage", back_populates="agent_run", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Model Usage (token & cost tracking)
# ─────────────────────────────────────────────
class ModelUsage(Base):
    __tablename__ = "model_usage"

    id = Column(String, primary_key=True, default=generate_uuid)
    agent_run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    model = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)  # google, groq
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    latency_ms = Column(Integer, nullable=True)
    cost = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    agent_run = relationship("AgentRun", back_populates="model_usage")


# ─────────────────────────────────────────────
# Audit Logs
# ─────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # upload, analyze, approve, delete, login, etc.
    resource_type = Column(String(50), nullable=True)  # contract, report, user
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="audit_logs")
