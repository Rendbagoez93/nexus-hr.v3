"""
apps/employees/schemas.py

Pydantic request/response schemas for Employee API.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreateSchema(BaseModel):
    """Schema for creating a linked AuthUser when registering an Employee."""

    email: EmailStr
    password: str = Field(min_length=8)


class EmployeeCreateSchema(BaseModel):
    """Schema for creating a new Employee."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field("", max_length=20)
    mobile_phone: str = Field("", max_length=20)
    gender: str = Field("other")
    date_of_birth: date | None = None
    place_of_birth: str = Field("", max_length=100)
    id_card_address: str = Field("", max_length=500)
    residential_address: str = Field("", max_length=500)
    department_id: str | None = None
    position_id: str | None = None
    status: str = Field("active")
    employment_type: str = Field("permanent")
    join_date: date
    base_salary: Decimal | None = Field(None, ge=0)
    direct_manager_id: str | None = None
    create_user: bool = Field(False, description="Also create an AuthUser for this employee")
    user_email: EmailStr | None = Field(None, description="Email for the AuthUser (required if create_user=true)")
    user_password: str | None = Field(None, min_length=8, description="Password for the AuthUser")

    @field_validator("gender")
    @classmethod
    def gender_must_be_valid(cls, v: str) -> str:
        valid = {"male", "female", "other"}
        if v not in valid:
            raise ValueError(f"gender must be one of: {', '.join(valid)}")
        return v

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        valid = {"active", "inactive", "resigned", "terminated"}
        if v not in valid:
            raise ValueError(f"status must be one of: {', '.join(valid)}")
        return v

    @field_validator("employment_type")
    @classmethod
    def employment_type_must_be_valid(cls, v: str) -> str:
        valid = {"permanent", "contract", "probation", "part_time", "intern"}
        if v not in valid:
            raise ValueError(f"employment_type must be one of: {', '.join(valid)}")
        return v


class EmployeeUpdateSchema(BaseModel):
    """Schema for updating an existing Employee (all fields optional)."""

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    mobile_phone: str | None = Field(None, max_length=20)
    gender: str | None = None
    date_of_birth: date | None = None
    place_of_birth: str | None = Field(None, max_length=100)
    id_card_address: str | None = Field(None, max_length=500)
    residential_address: str | None = Field(None, max_length=500)
    department_id: str | None = None
    position_id: str | None = None
    status: str | None = None
    employment_type: str | None = None
    join_date: date | None = None
    base_salary: Decimal | None = Field(None, ge=0)
    direct_manager_id: str | None = None

    @field_validator("gender")
    @classmethod
    def gender_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {"male", "female", "other"}
        if v not in valid:
            raise ValueError(f"gender must be one of: {', '.join(valid)}")
        return v

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {"active", "inactive", "resigned", "terminated"}
        if v not in valid:
            raise ValueError(f"status must be one of: {', '.join(valid)}")
        return v

    @field_validator("employment_type")
    @classmethod
    def employment_type_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {"permanent", "contract", "probation", "part_time", "intern"}
        if v not in valid:
            raise ValueError(f"employment_type must be one of: {', '.join(valid)}")
        return v


class DeactivateEmployeeSchema(BaseModel):
    """Schema for deactivating an Employee (resign/terminate)."""

    resign_date: date
    termination_reason: str = Field("", max_length=500)
