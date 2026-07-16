"""
apps/documents/schemas.py

Pydantic request schemas for EmployeeDocument API.

The uploaded file itself always arrives via ``request.FILES`` (multipart
upload) — these schemas validate only the accompanying metadata fields.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

from apps.documents.choices import DocumentType


class DocumentCreateSchema(BaseModel):
    """Schema for the metadata accompanying a new EmployeeDocument upload."""

    doc_type: str = Field(DocumentType.OTHER)
    valid_until: date | None = None

    @field_validator("doc_type")
    @classmethod
    def doc_type_must_be_valid(cls, v: str) -> str:
        valid = {choice.value for choice in DocumentType}
        if v not in valid:
            raise ValueError(f"doc_type must be one of: {', '.join(sorted(valid))}")
        return v


class DocumentUpdateSchema(BaseModel):
    """Schema for updating EmployeeDocument metadata (all fields optional)."""

    doc_type: str | None = None
    valid_until: date | None = None
    is_verified: bool | None = None

    @field_validator("doc_type")
    @classmethod
    def doc_type_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {choice.value for choice in DocumentType}
        if v not in valid:
            raise ValueError(f"doc_type must be one of: {', '.join(sorted(valid))}")
        return v
