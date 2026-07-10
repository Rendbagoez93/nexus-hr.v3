"""
apps/departments/tests/test_department_schemas.py

Unit tests for Pydantic schemas (DepartmentCreateRequest, DepartmentUpdateRequest).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from apps.departments.schemas import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
)


@pytest.mark.unit
class TestDepartmentCreateRequestSchema:
    def test_valid(self):
        """Valid payload parses without error."""
        schema = DepartmentCreateRequest(name="Engineering", code="ENG")
        assert schema.name == "Engineering"
        assert schema.code == "ENG"

    def test_code_uppercase(self):
        """code='eng' is uppercased to 'ENG'."""
        schema = DepartmentCreateRequest(name="Engineering", code="eng")
        assert schema.code == "ENG"

    def test_trims_whitespace(self):
        """code='  ENG  ' is trimmed to 'ENG'."""
        schema = DepartmentCreateRequest(name="Engineering", code="  ENG  ")
        assert schema.code == "ENG"

    def test_missing_name(self):
        """Missing name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DepartmentCreateRequest(code="ENG")
        assert "name" in str(exc_info.value)

    def test_missing_code(self):
        """Missing code raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DepartmentCreateRequest(name="Engineering")
        assert "code" in str(exc_info.value)

    def test_parent_id_optional(self):
        """parent_id is optional (None by default)."""
        schema = DepartmentCreateRequest(name="Engineering", code="ENG")
        assert schema.parent_id is None

    def test_parent_id_set(self):
        """parent_id can be set to a UUID string."""
        import uuid

        parent = str(uuid.uuid4())
        schema = DepartmentCreateRequest(
            name="Backend", code="BE", parent_id=parent
        )
        assert schema.parent_id == parent


@pytest.mark.unit
class TestDepartmentUpdateRequestSchema:
    def test_valid_partial(self):
        """Partial payload with only name parses without error."""
        schema = DepartmentUpdateRequest(name="New Name")
        assert schema.name == "New Name"
        assert schema.code is None

    def test_code_uppercase(self):
        """code='be' is uppercased to 'BE'."""
        schema = DepartmentUpdateRequest(code="be")
        assert schema.code == "BE"

    def test_null_code_preserved(self):
        """code=None is preserved (optional field)."""
        schema = DepartmentUpdateRequest(code=None)
        assert schema.code is None

    def test_parent_id_null(self):
        """parent_id=None is preserved."""
        schema = DepartmentUpdateRequest(parent_id=None)
        assert schema.parent_id is None

    def test_both_fields(self):
        """Both name and code provided."""
        schema = DepartmentUpdateRequest(name="New", code="NW")
        assert schema.name == "New"
        assert schema.code == "NW"
