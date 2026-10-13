"""
Utility functions for input validation and safe filename handling.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from fastapi import HTTPException, status

from app.config import get_settings

# Source code file extensions that are accepted for upload
ACCEPTED_EXTENSIONS = frozenset([
    "py", "js", "ts", "tsx", "java", "cpp", "cxx", "cc", "c", "h",
    "cs", "go", "rs", "kt", "swift", "rb", "php", "scala", "r",
    "julia", "jl", "dart", "lua", "pl", "pm", "hs", "ex", "exs",
    "sql", "sh", "bash", "ps1", "m", "f", "f90", "f95", "for",
    "asm", "s", "cob", "cbl", "sol", "erl", "hrl",
])

_UNSAFE_FILENAME_RE = re.compile(r"[^\w\-\._]")


def validate_code_size(code: str) -> None:
    """Raise HTTP 413 if code exceeds the configured maximum size."""
    settings = get_settings()
    if len(code.encode("utf-8")) > settings.max_code_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Source code exceeds the maximum allowed size of "
                f"{settings.max_code_size_kb} KB."
            ),
        )


def validate_code_not_empty(code: str) -> None:
    """Raise HTTP 422 if code is empty or whitespace only."""
    if not code or not code.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source code must not be empty.",
        )


def sanitize_filename(filename: Optional[str]) -> Optional[str]:
    """
    Return a sanitized filename safe for logging and display.
    Removes path traversal components and unsafe characters.
    Never used to construct filesystem paths.
    """
    if not filename:
        return None
    # Strip directory components
    basename = os.path.basename(filename)
    # Remove anything that isn't alphanumeric, dash, underscore, or dot
    safe = _UNSAFE_FILENAME_RE.sub("_", basename)
    return safe[:128]  # truncate to reasonable length


def validate_file_extension(filename: str) -> None:
    """Raise HTTP 415 if the file extension is not in the accepted set."""
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    if ext not in ACCEPTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File extension '.{ext}' is not accepted. "
                f"Supported extensions: {', '.join(sorted(ACCEPTED_EXTENSIONS))}."
            ),
        )


def decode_file_content(raw_bytes: bytes, filename: str) -> str:
    """
    Safely decode uploaded file bytes to a string.
    Tries UTF-8, then falls back to latin-1.
    """
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw_bytes.decode("latin-1")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not decode file '{filename}' as text.",
            )
