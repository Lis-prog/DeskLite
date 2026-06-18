from __future__ import annotations

from pathlib import Path

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".txt",
        ".doc",
        ".docx",
    }
)

ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)


class FileValidationError(ValueError):
    """Raised when an upload fails type or size checks."""


def validate_upload(filename: str, content_type: str, size: int) -> None:
    """Reject disallowed file types and oversized uploads with a clear message."""
    if not filename or not filename.strip():
        raise FileValidationError("Filename is required.")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise FileValidationError(
            f"File type '{extension or '(none)'}' is not allowed. "
            f"Allowed extensions: {allowed}."
        )

    normalized_type = (content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if normalized_type not in ALLOWED_CONTENT_TYPES:
        raise FileValidationError(
            f"Content type '{normalized_type}' is not allowed."
        )

    if size <= 0:
        raise FileValidationError("File is empty.")

    if size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise FileValidationError(
            f"File exceeds maximum size of {max_mb} MB."
        )
