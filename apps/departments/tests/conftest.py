"""
apps/departments/tests/conftest.py

Department- and Position-specific fixtures for the departments module test suite.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from apps.companies.models import Company
    from apps.departments.models import Department, Position


@pytest.fixture
def company(db) -> "Company":
    """Company for department tests (reuses a single company per test)."""
    from apps.companies.models import Company

    return Company.objects.create(
        name="Test Company",
        industry="manufacturing",
        subscription_tier="core",
        is_active=True,
    )


@pytest.fixture
def department(db, company: "Company") -> "Department":
    """Active Department belonging to company."""
    from apps.departments.models import Department

    return Department.objects.create(
        company=company,
        name="Engineering",
        code="ENG",
    )


@pytest.fixture
def inactive_department(db, company: "Company") -> "Department":
    """Soft-deleted Department."""
    from apps.departments.models import Department

    dept = Department.objects.create(
        company=company,
        name="Deprecated",
        code="DEP",
    )
    dept.deactivate()
    return dept


@pytest.fixture
def two_departments(db, company: "Company") -> tuple["Department", "Department"]:
    """Two active departments for hierarchy tests."""
    from apps.departments.models import Department

    parent = Department.objects.create(company=company, name="Operations", code="OPS")
    child = Department.objects.create(
        company=company, name="Maintenance", code="MNT", parent=parent
    )
    return parent, child


@pytest.fixture
def department_other_company(db) -> "Department":
    """Department owned by a second company — for cross-tenant isolation tests."""
    from apps.companies.models import Company
    from apps.departments.models import Department

    other_co = Company.objects.create(
        name="Other Corp",
        industry="office",
        subscription_tier="core",
        is_active=True,
    )
    return Department.objects.create(
        company=other_co,
        name="Other Dept",
        code="OTH",
    )


@pytest.fixture
def position(
    db, company: "Company", department: "Department"
) -> "Position":
    """Active Position within department."""
    from apps.departments.models import Position

    return Position.objects.create(
        company=company,
        department=department,
        title="Software Engineer",
        level="staff",
        base_salary_min=Decimal("5000000"),
        base_salary_max=Decimal("8000000"),
    )


@pytest.fixture
def inactive_position(
    db, company: "Company", department: "Department"
) -> "Position":
    """Soft-deleted Position."""
    from apps.departments.models import Position

    pos = Position.objects.create(
        company=company,
        department=department,
        title="Contractor",
        level="staff",
        base_salary_min=Decimal("3000000"),
        base_salary_max=Decimal("4000000"),
    )
    pos.deactivate()
    return pos


@pytest.fixture
def position_other_company(db) -> "Position":
    """Position owned by a second company."""
    from apps.companies.models import Company
    from apps.departments.models import Department, Position

    other_co = Company.objects.create(
        name="Other Corp",
        industry="office",
        subscription_tier="core",
        is_active=True,
    )
    dept = Department.objects.create(company=other_co, name="Other Dept", code="OTH")
    return Position.objects.create(
        company=other_co,
        department=dept,
        title="Other Position",
        level="staff",
        base_salary_min=Decimal("5000000"),
        base_salary_max=Decimal("8000000"),
    )


@pytest.fixture
def hr_admin_client(db) -> "APIClient":
    """Authenticated APIClient for an HR Admin user."""
    from rest_framework.test import APIClient
    from tests.factories import HRAdminFactory

    user = HRAdminFactory()
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    # Store on handler so tests can access via client.handler._force_user
    api_client.handler._force_user = user
    return api_client


@pytest.fixture
def other_company_client(db) -> "APIClient":
    """APIClient authenticated as HR Admin in a second company."""
    from rest_framework.test import APIClient
    from tests.factories import HRAdminFactory

    user = HRAdminFactory()
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    api_client.handler._force_user = user
    return api_client


@pytest.fixture
def manager_client(db) -> "APIClient":
    """Authenticated APIClient for a Manager user."""
    from rest_framework.test import APIClient
    from tests.factories import ManagerFactory

    user = ManagerFactory()
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    api_client.handler._force_user = user
    return api_client


@pytest.fixture
def employee_client(db) -> "APIClient":
    """Authenticated APIClient for an Employee user."""
    from rest_framework.test import APIClient
    from tests.factories import EmployeeUserFactory

    user = EmployeeUserFactory()
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    api_client.handler._force_user = user
    return api_client


@pytest.fixture
def hse_officer_client(db) -> "APIClient":
    """Authenticated APIClient for an HSE Officer user."""
    from rest_framework.test import APIClient
    from tests.factories import HSEOfficerFactory

    user = HSEOfficerFactory()
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    api_client.handler._force_user = user
    return api_client


@pytest.fixture
def platform_admin_client(db) -> "APIClient":
    """Authenticated APIClient for a platform admin (superuser, no company)."""
    from rest_framework.test import APIClient
    from tests.factories import PlatformAdminFactory

    user = PlatformAdminFactory()
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    api_client.handler._force_user = user
    return api_client
