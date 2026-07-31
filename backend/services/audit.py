"""
ContractIQ — Audit Logging Service

Utility for logging all significant actions to the audit_logs table.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.models import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Log an action to the audit_logs table.

    Args:
        db: Database session
        action: Action name (upload, analyze, approve, delete, login, etc.)
        user_id: ID of the user performing the action
        resource_type: Type of resource (contract, report, user)
        resource_id: ID of the affected resource
        details: Additional details as JSON
        ip_address: Client IP address
    """
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(audit_log)
