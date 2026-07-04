"""
apps/shared/utils/ids.py

ID and number generation helpers.
"""

import secrets
import uuid
from datetime import datetime


def generate_uuid() -> uuid.UUID:
    return uuid.uuid4()


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def generate_emp_number(company_prefix: str, sequence: int) -> str:
    """
    Generate an employee number in format: {PREFIX}-{SEQ:04d}

    Example:
        generate_emp_number("NXS", 1)   → "NXS-0001"
        generate_emp_number("ACME", 42)  → "ACME-0042"
    """
    return f"{company_prefix.upper()}-{sequence:04d}"


def generate_document_key(company_id: int, employee_id: int, filename: str) -> str:
    """
    Generate an S3 key for employee documents.

    Format: documents/{company_id}/{employee_id}/{YYYY}/{MM}/{uuid}/{filename}
    """
    now = datetime.utcnow()
    safe_filename = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
    return (
        f"documents/{company_id}/{employee_id}/"
        f"{now.year}/{now.month:02d}/"
        f"{uuid.uuid4()}/{safe_filename}"
    )
