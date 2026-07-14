"""
apps/departments/schemas.py

Pydantic request/response schemas for Department and Position APIs.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DepartmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=20)
    parent_id: str | None = Field(None, description="UUID of parent department")
    is_active: bool = Field(True)

    @field_validator("code")
    @classmethod
    def code_upper(cls, v: str) -> str:
        return v.strip().upper()


class DepartmentUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=20)
    parent_id: str | None = Field(None)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def code_upper(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip().upper()
        return v


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    code: str
    name: str
    parent_id: str | None
    is_active: bool
    created_at: str
    updated_at: str


class PositionCreateRequest(BaseModel):
    department_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=255)
    level: str = Field(min_length=1, max_length=20)
    base_salary_min: Decimal = Field(ge=0)
    base_salary_max: Decimal = Field(ge=0)
    is_active: bool = Field(True)

    @field_validator("base_salary_max")
    @classmethod
    def salary_max_not_less_than_min(cls, v: Decimal, info) -> Decimal:
        if "base_salary_min" in info.data and v < info.data["base_salary_min"]:
            raise ValueError("base_salary_max must be >= base_salary_min")
        return v


class PositionUpdateRequest(BaseModel):
    department_id: str | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    level: str | None = Field(None, min_length=1, max_length=20)
    base_salary_min: Decimal | None = Field(None, ge=0)
    base_salary_max: Decimal | None = Field(None, ge=0)
    is_active: bool | None = None

    @field_validator("base_salary_max")
    @classmethod
    def salary_max_not_less_than_min(cls, v: Decimal | None, info) -> Decimal | None:
        if v is not None and "base_salary_min" in info.data:
            min_val = info.data["base_salary_min"]
            if min_val is not None and v < min_val:
                raise ValueError("base_salary_max must be >= base_salary_min")
        return v


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    department_id: str
    title: str
    level: str
    base_salary_min: Decimal
    base_salary_max: Decimal
    is_active: bool
    created_at: str
    updated_at: str
