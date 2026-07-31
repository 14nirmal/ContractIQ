"""
ContractIQ — Authentication Routes

POST /signup — register new user
POST /login  — authenticate and return JWT
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import create_access_token, hash_password, verify_password
from backend.database.connection import get_db
from backend.database.models import User, AuditLog
from backend.schemas.auth import UserCreate, UserLogin, UserResponse, Token

router = APIRouter(prefix="/api", tags=["Authentication"])


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    await db.flush()

    # Create audit log
    audit_log = AuditLog(
        user_id=user.id,
        action="signup",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email},
    )
    db.add(audit_log)

    # Generate JWT token
    access_token = create_access_token(data={"sub": user.id, "email": user.email})

    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT token."""
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Create audit log
    audit_log = AuditLog(
        user_id=user.id,
        action="login",
        resource_type="user",
        resource_id=user.id,
    )
    db.add(audit_log)

    # Generate JWT token
    access_token = create_access_token(data={"sub": user.id, "email": user.email})

    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )
