"""
apps/shared/utils/storage.py

S3 / Django file storage helpers.
"""

from datetime import datetime, timedelta, timezone
from typing import BinaryIO

from django.core.files.storage import get_storage_class

from apps.shared.utils.ids import generate_document_key


def get_storage():
    """Return the configured default storage backend (S3 or filesystem)."""
    return get_storage_class()()


def upload_file(
    file_obj: BinaryIO,
    key: str,
    content_type: str | None = None,
    acl: str = "private",
) -> str:
    """
    Upload a file to the configured storage backend.

    Returns the storage key (URL path) on success.

    Args:
        file_obj: File-like object to upload.
        key: Storage key (path) for the file.
        content_type: MIME type (used for S3 Content-Type header).
        acl: S3 canned ACL. Default 'private'.
    """
    storage = get_storage()
    kwargs: dict = {}
    if content_type:
        kwargs["content_type"] = content_type
    if hasattr(storage, "bucket") and acl:
        # boto3 / S3 backend
        kwargs["extra_args"] = {"ACL": acl}

    saved = storage.save(key, file_obj, **kwargs)
    return saved


def generate_signed_url(
    key: str,
    expires_in_minutes: int = 15,
) -> str:
    """
    Generate a time-limited signed URL for a stored file.

    Uses the storage backend's built-in signed URL generation.
    Falls back to returning the relative URL for non-S3 backends.
    """
    storage = get_storage()

    if hasattr(storage, "url"):
        # S3 / boto3 backend
        return storage.url(key, expire=expires_in_minutes * 60)

    # Local filesystem fallback
    return storage.url(key)


def delete_file(key: str) -> bool:
    """
    Delete a file from storage by its key.
    Returns True if deleted, False if it didn't exist.
    """
    storage = get_storage()
    try:
        storage.delete(key)
        return True
    except Exception:  # noqa: BLE001
        return False


def generate_document_upload_key(
    company_id: int,
    employee_id: int,
    filename: str,
) -> str:
    """Generate a well-structured S3 key for an employee document upload."""
    return generate_document_key(company_id, employee_id, filename)
