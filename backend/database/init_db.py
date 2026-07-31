"""
ContractIQ — Database Initialization

Creates all tables on startup.
"""

import asyncio
from backend.database.connection import engine, Base

# Import all models so SQLAlchemy registers them
from backend.database.models import (  # noqa: F401
    User,
    Contract,
    ContractVersion,
    Clause,
    Embedding,
    RiskReport,
    Approval,
    AgentRun,
    ModelUsage,
    AuditLog,
)


async def init_database():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Database tables created successfully.")


async def drop_database():
    """Drop all database tables (use with caution)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("[WARNING] All database tables dropped.")


if __name__ == "__main__":
    asyncio.run(init_database())
