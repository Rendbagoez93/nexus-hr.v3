"""
apps/shared/utils/storage.py

S3 / Django file storage helpers.
"""

from datetime import datetime, timedelta, timezone
from typing import BinaryIO

from django.core.files.storage import default_storage

from apps.shared.utils.ids import generate_document_key


def get_storage():
    """Return the configured default storage backend (S3 or filesystem)."""
    return default_storage


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
        content_type: MIME type (used for S3 Content-Type header). django-storages'
            S3Boto3Storage infers this automatically from the file name/content, so
            it isn't passed through explicitly here.
        acl: S3 canned ACL. Default 'private'. Configured at the storage-class level
            (AWS_DEFAULT_ACL / AWS_S3_OBJECT_PARAMETERS in settings), not per-call.
    """
    storage = get_storage()
    saved = storage.save(key, file_obj)
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

    if hasattr(storage, "bucket"):
        # S3 / boto3 backend — supports an `expire` (seconds) kwarg.
        return storage.url(key, expire=expires_in_minutes * 60)

    # Local filesystem fallback — Storage.url() takes no expiry kwarg.
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
