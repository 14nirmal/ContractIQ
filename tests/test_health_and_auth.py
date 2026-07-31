"""
ContractIQ — Core Health & Auth Unit Tests
"""

import pytest
from backend.auth.security import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing():
    """Verify bcrypt password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    """Verify JWT token encoding and decoding."""
    payload = {"sub": "user-123-abc", "email": "test@contractiq.com"}
    token = create_access_token(data=payload)
    
    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-123-abc"
    assert decoded["email"] == "test@contractiq.com"
