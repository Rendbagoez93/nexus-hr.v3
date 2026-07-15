"""
apps/employees/tests/conftest.py — Fixtures for employees tests.

Scope strategy:
  session    — (none needed yet)
  module     — company, department, position (read-only reference data)
  function   — All employee fixtures (tests create/mutate employee data)
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from apps.companies.models import Company
    from apps.departments.models import Department, Position
    from apps.employees.models import Employee
    from apps.users.models import AuthUser


# ---------------------------------------------------------------------------
# Company fixture (module-scoped — read-only reference for the test file)
# ---------------------------------------------------------------------------

@pytest.fixture
def company(db) -> "Company":
    """Active Company for employee tests."""
    from apps.companies.models import Company

    return Company.objects.create(
        name="Nexus Test Corp",
        industry="manufacturing",
        subscription_tier="core",
        is_active=True,
        emp_number_prefix="NXT",
        geofence_radius_meters=100,
    )


# ---------------------------------------------------------------------------
# Department fixture (module-scoped — read-only reference)
# ---------------------------------------------------------------------------

@pytest.fixture
def department(db, company: "Company") -> "Department":
    """Active Department belonging to company."""
    from apps.departments.models import Department

    return Department.objects.create(
        company=company,
        name="Engineering",
        code="ENG",
    )


# ---------------------------------------------------------------------------
# Position fixture (module-scoped — read-only reference)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Function-scoped employee fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def employee(db, company: "Company", department: "Department", position: "Position") -> "Employee":
    """A standard active Employee instance."""
    from apps.employees.models import Employee

    return Employee.objects.create(
        company=company,
        emp_number="NXS-0001",
        first_name="John",
        last_name="Doe",
        email="john.doe@nexus.test",
        phone="081234567890",
        mobile_phone="081234567891",
        gender="male",
        date_of_birth="1990-01-15",
        place_of_birth="Jakarta",
        id_card_address="Jl. Sudirman No.1, Jakarta",
        residential_address="Jl. Thamrin No.2, Jakarta",
        department=department,
        position=position,
        status="active",
        employment_type="permanent",
        join_date="2020-01-01",
        base_salary=Decimal("10000000.00"),
    )


@pytest.fixture
def employee_other_company(db) -> "Employee":
    """Employee owned by a second company — for cross-tenant isolation tests."""
    from apps.companies.models import Company
    from apps.departments.models import Department
    from apps.employees.models import Employee

    other_co = Company.objects.create(
        name="Other Corp",
        industry="office",
        subscription_tier="core",
        is_active=True,
        emp_number_prefix="OTH",
    )
    other_dept = Department.objects.create(
        company=other_co,
        name="Other Department",
        code="OTH",
    )
    return Employee.objects.create(
        company=other_co,
        emp_number="OTH-0001",
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@other.test",
        department=other_dept,
        status="active",
        employment_type="permanent",
        join_date="2021-06-01",
    )


@pytest.fixture
def inactive_employee(db, company: "Company", department: "Department") -> "Employee":
    """Soft-deleted Employee (is_active=False)."""
    from apps.employees.models import Employee

    emp = Employee.objects.create(
        company=company,
        emp_number="NXS-0002",
        first_name="Bob",
        last_name="Inactive",
        email="bob.inactive@nexus.test",
        department=department,
        status="inactive",
        employment_type="permanent",
        join_date="2019-03-01",
    )
    emp.deactivate()
    return emp


@pytest.fixture
def resigned_employee(db, company: "Company", department: "Department") -> "Employee":
    """Employee with RESIGNED status (still is_active=True)."""
    from apps.employees.models import Employee
    from datetime import date

    return Employee.objects.create(
        company=company,
        emp_number="NXS-0003",
        first_name="Alice",
        last_name="Resigned",
        email="alice.resigned@nexus.test",
        department=department,
        status="resigned",
        employment_type="permanent",
        join_date="2018-01-01",
        resign_date=date(2025, 12, 31),
    )


@pytest.fixture
def terminated_employee(db, company: "Company", department: "Department") -> "Employee":
    """Employee with TERMINATED status."""
    from apps.employees.models import Employee
    from datetime import date

    return Employee.objects.create(
        company=company,
        emp_number="NXS-0004",
        first_name="Charlie",
        last_name="Terminated",
        email="charlie.terminated@nexus.test",
        department=department,
        status="terminated",
        employment_type="permanent",
        join_date="2017-01-01",
        termination_date=date(2025, 6, 30),
        termination_reason="Gross misconduct",
    )


@pytest.fixture
def probation_employee(db, company: "Company", department: "Department", position: "Position") -> "Employee":
    """Employee on probation."""
    from apps.employees.models import Employee

    return Employee.objects.create(
        company=company,
        emp_number="NXS-0005",
        first_name="Dave",
        last_name="Probation",
        email="dave.probation@nexus.test",
        department=department,
        position=position,
        status="active",
        employment_type="probation",
        join_date="2026-01-01",
        base_salary=Decimal("7000000.00"),
    )


@pytest.fixture
def contract_employee(db, company: "Company", department: "Department") -> "Employee":
    """Contract employee."""
    from apps.employees.models import Employee

    return Employee.objects.create(
        company=company,
        emp_number="NXS-0006",
        first_name="Eve",
        last_name="Contract",
        email="eve.contract@nexus.test",
        department=department,
        status="active",
        employment_type="contract",
        join_date="2025-01-01",
        base_salary=Decimal("12000000.00"),
    )


@pytest.fixture
def employee_with_user(db, company: "Company", department: "Department", position: "Position") -> "Employee":
    """Employee linked to an AuthUser."""
    from apps.employees.models import Employee
    from apps.users.models import AuthUser

    user = AuthUser.objects.create_user(
        email="linked.user@nexus.test",
        password="TestPass123!",
        role="employee",
        company=company,
    )
    return Employee.objects.create(
        company=company,
        user=user,
        emp_number="NXS-0007",
        first_name="Frank",
        last_name="Linked",
        email="linked.user@nexus.test",
        department=department,
        position=position,
        status="active",
        employment_type="permanent",
        join_date="2022-01-01",
        base_salary=Decimal("15000000.00"),
    )


@pytest.fixture
def two_employees(db, company: "Company", department: "Department") -> tuple["Employee", "Employee"]:
    """Two employees for comparison/filtering tests."""
    from apps.employees.models import Employee

    emp1 = Employee.objects.create(
        company=company,
        emp_number="NXS-0010",
        first_name="George",
        last_name="First",
        email="george.first@nexus.test",
        department=department,
        status="active",
        employment_type="permanent",
        join_date="2020-01-01",
    )
    emp2 = Employee.objects.create(
        company=company,
        emp_number="NXS-0011",
        first_name="Hannah",
        last_name="Second",
        email="hannah.second@nexus.test",
        department=department,
        status="active",
        employment_type="contract",
        join_date="2021-06-01",
    )
    return emp1, emp2


@pytest.fixture
def two_companies(db) -> tuple["Company", "Company"]:
    """Two distinct active companies for cross-tenant isolation tests."""
    from apps.companies.models import Company

    alpha = Company.objects.create(
        name="Company Alpha",
        industry="manufacturing",
        subscription_tier="core",
        is_active=True,
        emp_number_prefix="ALP",
    )
    beta = Company.objects.create(
        name="Company Beta",
        industry="construction",
        subscription_tier="payroll",
        is_active=True,
        emp_number_prefix="BTX",
    )
    return alpha, beta


# ---------------------------------------------------------------------------
# Authenticated API clients
# ---------------------------------------------------------------------------

@pytest.fixture
def hr_admin_client(db, company: "Company"):
    """Authenticated APIClient for an HR Admin within company."""
    from rest_framework.test import APIClient
    from tests.factories import HRAdminFactory

    user = HRAdminFactory(company=company)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def manager_client(db, company: "Company"):
    """Authenticated APIClient for a Manager within company."""
    from rest_framework.test import APIClient
    from tests.factories import ManagerFactory

    user = ManagerFactory(company=company)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def employee_client(db, employee_with_user: "Employee"):
    """
    Authenticated APIClient for a plain Employee within company.

    Authenticated as the AuthUser linked to `employee_with_user`, so tests
    that assert "own record" access can request that employee's record
    and get a match.
    """
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=employee_with_user.user)
    return client


@pytest.fixture
def other_company_client(db, employee_other_company: "Employee"):
    """APIClient authenticated as HR Admin in a second, unrelated company."""
    from rest_framework.test import APIClient
    from tests.factories import HRAdminFactory

    user = HRAdminFactory(company=employee_other_company.company)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def platform_admin_client(db):
    """APIClient authenticated as a platform admin (superuser, no company)."""
    from rest_framework.test import APIClient
    from tests.factories import PlatformAdminFactory

    user = PlatformAdminFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client
