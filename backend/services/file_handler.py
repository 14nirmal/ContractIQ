"""
ContractIQ — File Handler Service

Handles file upload, validation, and storage.
"""

import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from backend.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes


def validate_file(file: UploadFile) -> str:
    """
    Validate uploaded file type and size.
    Returns the file extension.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    return ext


async def save_upload(file: UploadFile, user_id: str) -> tuple[str, str]:
    """
    Save uploaded file to disk with unique naming.
    Returns (file_path, file_type).
    """
    ext = validate_file(file)

    # Create user-specific upload directory
    upload_dir = Path(settings.UPLOAD_DIR) / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / unique_name

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit",
        )

    # Write file to disk
    with open(file_path, "wb") as f:
        f.write(content)

    return str(file_path), ext.lstrip(".")


def delete_file(file_path: str) -> bool:
    """Delete a file from disk. Returns True if successful."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except OSError:
        return False
