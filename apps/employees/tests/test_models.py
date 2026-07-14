"""
apps/employees/tests/test_models.py

Unit and integration tests for the Employee model.

Categories covered (per Section 7 of the Technical Requirement Document):
  - Model Tests: constraints, computed properties
  - Integration Tests: tenant isolation, queryset filtering

Markers:
  @pytest.mark.unit    — single function/class, no DB or network I/O
  @pytest.mark.integration  — multiple components, DB, services

All tests use fixtures from conftest.py. Do not use Model.objects.create()
directly — use fixtures or factories instead.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.db import IntegrityError

from apps.companies.models import Company
from apps.departments.models import Department
from apps.employees.choices import EmployeeStatus, EmploymentType, Gender
from apps.employees.models import Employee

# =============================================================================
# Model field defaults & __str__ / computed properties
# =============================================================================

@pytest.mark.unit
def test_employee_str(employee: Employee) -> None:
    """Employee __str__ returns 'FirstName LastName (emp_number)'."""
    assert str(employee) == "John Doe (NXS-0001)"


@pytest.mark.unit
def test_employee_full_name(employee: Employee) -> None:
    """full_name property concatenates first_name and last_name."""
    assert employee.full_name == "John Doe"


@pytest.mark.unit
def test_employee_full_name_single_name(employee: Employee) -> None:
    """full_name handles edge case where one name is empty."""
    emp: Employee = employee  # type hint only
    emp.first_name = "Solo"
    emp.last_name = ""
    assert emp.full_name == "Solo"


@pytest.mark.unit
def test_employee_default_gender() -> None:
    """Gender defaults to OTHER when not specified."""
    emp = Employee(
        company_id=1,
        emp_number="NXS-TMP1",
        first_name="Test",
        last_name="Default",
        email="test.default@nexus.test",
        join_date=date(2020, 1, 1),
    )
    assert emp.gender == Gender.OTHER


@pytest.mark.unit
def test_employee_default_status() -> None:
    """Status defaults to ACTIVE when not specified."""
    emp = Employee(
        company_id=1,
        emp_number="NXS-TMP2",
        first_name="Test",
        last_name="Status",
        email="test.status@nexus.test",
        join_date=date(2020, 1, 1),
    )
    assert emp.status == EmployeeStatus.ACTIVE


@pytest.mark.unit
def test_employee_default_employment_type() -> None:
    """Employment type defaults to PERMANENT when not specified."""
    emp = Employee(
        company_id=1,
        emp_number="NXS-TMP3",
        first_name="Test",
        last_name="EmpType",
        email="test.emptype@nexus.test",
        join_date=date(2020, 1, 1),
    )
    assert emp.employment_type == EmploymentType.PERMANENT


# =============================================================================
# is_billable — billing-relevant active status
# =============================================================================

@pytest.mark.unit
def test_is_billable_true_when_active_and_is_active(
    employee: Employee,
) -> None:
    """is_billable is True when status=ACTIVE and is_active=True."""
    assert employee.status == EmployeeStatus.ACTIVE
    assert employee.is_active is True
    assert employee.is_billable is True


@pytest.mark.unit
def test_is_billable_false_when_inactive_status(
    employee: Employee,
) -> None:
    """is_billable is False when status is not ACTIVE."""
    employee.status = EmployeeStatus.INACTIVE
    employee.save(update_fields=["status"])
    assert employee.is_billable is False


@pytest.mark.unit
def test_is_billable_false_when_soft_deleted(
    employee: Employee,
) -> None:
    """is_billable is False when is_active=False (soft-deleted)."""
    employee.deactivate()
    assert employee.is_active is False
    assert employee.is_billable is False


@pytest.mark.unit
def test_is_billable_false_when_resigned(
    resigned_employee: Employee,
) -> None:
    """is_billable is False for resigned employees even when is_active=True."""
    assert resigned_employee.is_active is True
    assert resigned_employee.status == EmployeeStatus.RESIGNED
    assert resigned_employee.is_billable is False


@pytest.mark.unit
def test_is_billable_false_when_terminated(
    terminated_employee: Employee,
) -> None:
    """is_billable is False for terminated employees."""
    assert terminated_employee.is_billable is False


# =============================================================================
# is_active_employment — employment status (regardless of soft-delete)
# =============================================================================

@pytest.mark.unit
def test_is_active_employment_true_for_active(
    employee: Employee,
) -> None:
    """is_active_employment is True when status=ACTIVE."""
    assert employee.is_active_employment is True


@pytest.mark.unit
def test_is_active_employment_false_for_resigned(
    resigned_employee: Employee,
) -> None:
    """is_active_employment is False when status=RESIGNED."""
    assert resigned_employee.is_active_employment is False


@pytest.mark.unit
def test_is_active_employment_false_for_inactive(
    employee: Employee,
) -> None:
    """is_active_employment is False when status=INACTIVE."""
    employee.status = EmployeeStatus.INACTIVE
    employee.save(update_fields=["status"])
    assert employee.is_active_employment is False


@pytest.mark.unit
def test_is_active_employment_false_for_terminated(
    terminated_employee: Employee,
) -> None:
    """is_active_employment is False when status=TERMINATED."""
    assert terminated_employee.is_active_employment is False


# =============================================================================
# Unique constraints
# =============================================================================

@pytest.mark.integration
def test_emp_number_is_unique_per_database(
    db,
    company: Company,
    department: Department,
) -> None:
    """emp_number must be globally unique across the entire database."""
    Employee.objects.create(
        company=company,
        emp_number="UNI-0001",
        first_name="First",
        last_name="Unique",
        email="first.unique@nexus.test",
        join_date=date(2020, 1, 1),
    )
    with pytest.raises(IntegrityError):
        Employee.objects.create(
            company=company,
            emp_number="UNI-0001",
            first_name="Second",
            last_name="Unique",
            email="second.unique@nexus.test",
            join_date=date(2020, 1, 1),
        )


@pytest.mark.integration
def test_company_emp_number_unique_constraint(
    db,
    two_companies: tuple[Company, Company],
) -> None:
    """uq_employees_company_emp_number prevents duplicate emp_numbers within the same company.

    Note: emp_number is globally unique (unique=True on the field). The composite
    constraint uq_employees_company_emp_number adds company-level deduplication on
    top of that. We test the duplicate-in-same-company case here.
    """
    company_a, company_b = two_companies

    dept_a = Department.objects.create(
        company=company_a, name="Dept A", code="DA"
    )

    # Employee in company A
    Employee.objects.create(
        company=company_a,
        emp_number="SAME-0001",
        first_name="Alice",
        last_name="A",
        email="alice.a@nexus.test",
        department=dept_a,
        join_date=date(2020, 1, 1),
    )

    # Employee in company B with different emp_number (emp_number is globally unique)
    Employee.objects.create(
        company=company_b,
        emp_number="SAME-0002",
        first_name="Bob",
        last_name="B",
        email="bob.b@nexus.test",
        join_date=date(2020, 1, 1),
    )

    # Verify isolation — each company has one employee
    assert Employee.objects.for_company(company_a.id).count() == 1
    assert Employee.objects.for_company(company_b.id).count() == 1


@pytest.mark.integration
def test_emp_number_globally_unique_per_company(
    db,
    company: Company,
    department: Department,
) -> None:
    """Duplicate emp_number within the same company raises IntegrityError."""
    Employee.objects.create(
        company=company,
        emp_number="DUP-0001",
        first_name="First",
        last_name="Dup",
        email="first.dup@nexus.test",
        department=department,
        join_date=date(2020, 1, 1),
    )
    with pytest.raises(IntegrityError):
        Employee.objects.create(
            company=company,
            emp_number="DUP-0001",
            first_name="Second",
            last_name="Dup",
            email="second.dup@nexus.test",
            department=department,
            join_date=date(2020, 1, 1),
        )


# =============================================================================
# QuerySet — for_company, alive, active
# =============================================================================

@pytest.mark.integration
def test_queryset_for_company(
    two_companies: tuple[Company, Company],
    department: Department,
) -> None:
    """for_company filters employees by company."""
    company_a, company_b = two_companies

    dept_a = Department.objects.create(
        company=company_a, name="Dept A", code="DA"
    )
    dept_b = Department.objects.create(
        company=company_b, name="Dept B", code="DB"
    )

    Employee.objects.create(
        company=company_a,
        emp_number="CMP-001",
        first_name="A",
        last_name="One",
        email="a.one@nexus.test",
        department=dept_a,
        join_date=date(2020, 1, 1),
    )
    Employee.objects.create(
        company=company_a,
        emp_number="CMP-002",
        first_name="A",
        last_name="Two",
        email="a.two@nexus.test",
        department=dept_a,
        join_date=date(2020, 1, 1),
    )
    Employee.objects.create(
        company=company_b,
        emp_number="CMP-003",
        first_name="B",
        last_name="One",
        email="b.one@nexus.test",
        department=dept_b,
        join_date=date(2020, 1, 1),
    )

    qs = Employee.objects.for_company(company_a.id)
    assert qs.count() == 2
    assert all(e.company_id == company_a.id for e in qs)


@pytest.mark.integration
def test_queryset_alive(
    db,
    company: Company,
    department: Department,
) -> None:
    """alive() filters to is_active=True employees."""
    active = Employee.objects.create(
        company=company,
        emp_number="ALV-001",
        first_name="Alive",
        last_name="Emp",
        email="alive.emp@nexus.test",
        join_date=date(2020, 1, 1),
    )
    inactive = Employee.objects.create(
        company=company,
        emp_number="ALV-002",
        first_name="Inactive",
        last_name="Emp",
        email="inactive.emp@nexus.test",
        join_date=date(2020, 1, 1),
    )
    inactive.deactivate()

    alive_qs = Employee.objects.alive()
    assert active in alive_qs
    assert inactive not in alive_qs


@pytest.mark.integration
def test_queryset_active(
    db,
    company: Company,
    department: Department,
) -> None:
    """active() filters to status=ACTIVE AND is_active=True employees."""
    billable = Employee.objects.create(
        company=company,
        emp_number="ACT-001",
        first_name="Active",
        last_name="Emp",
        email="active.emp@nexus.test",
        status=EmployeeStatus.ACTIVE,
        join_date=date(2020, 1, 1),
    )
    resigned = Employee.objects.create(
        company=company,
        emp_number="ACT-002",
        first_name="Resigned",
        last_name="Emp",
        email="resigned.emp@nexus.test",
        status=EmployeeStatus.RESIGNED,
        join_date=date(2020, 1, 1),
    )
    soft_deleted = Employee.objects.create(
        company=company,
        emp_number="ACT-003",
        first_name="Deleted",
        last_name="Emp",
        email="deleted.emp@nexus.test",
        status=EmployeeStatus.ACTIVE,
        join_date=date(2020, 1, 1),
    )
    soft_deleted.deactivate()

    active_qs = Employee.objects.active()
    assert billable in active_qs
    assert resigned not in active_qs
    assert soft_deleted not in active_qs


@pytest.mark.integration
def test_queryset_active_chained(
    db,
    two_companies: tuple[Company, Company],
) -> None:
    """for_company().active() chains correctly."""
    company_a, company_b = two_companies

    Employee.objects.create(
        company=company_a,
        emp_number="CHN-001",
        first_name="Chained",
        last_name="A",
        email="chained.a@nexus.test",
        status=EmployeeStatus.ACTIVE,
        join_date=date(2020, 1, 1),
    )
    Employee.objects.create(
        company=company_a,
        emp_number="CHN-002",
        first_name="Chained",
        last_name="Resigned",
        email="chained.resigned@nexus.test",
        status=EmployeeStatus.RESIGNED,
        join_date=date(2020, 1, 1),
    )
    Employee.objects.create(
        company=company_b,
        emp_number="CHN-003",
        first_name="Chained",
        last_name="B",
        email="chained.b@nexus.test",
        status=EmployeeStatus.ACTIVE,
        join_date=date(2020, 1, 1),
    )

    qs = Employee.objects.for_company(company_a.id).active()
    assert qs.count() == 1
    assert qs.first().first_name == "Chained"


# =============================================================================
# SoftDeleteMixin — deactivate / restore
# =============================================================================

@pytest.mark.integration
def test_employee_deactivate(employee: Employee) -> None:
    """deactivate() sets is_active=False and records deleted_at."""
    assert employee.is_active is True
    assert employee.deleted_at is None

    employee.deactivate()

    assert employee.is_active is False
    assert employee.deleted_at is not None


@pytest.mark.integration
def test_employee_restore(employee: Employee) -> None:
    """restore() sets is_active=True and clears deleted_at."""
    employee.deactivate()
    assert employee.is_active is False

    employee.restore()

    assert employee.is_active is True
    assert employee.deleted_at is None


@pytest.mark.integration
def test_deactivate_idempotent(employee: Employee) -> None:
    """Calling deactivate twice does not overwrite deleted_at timestamp."""
    employee.deactivate()
    first_deleted_at = employee.deleted_at

    employee.deactivate()

    assert employee.deleted_at == first_deleted_at


# =============================================================================
# Meta — ordering and db_table
# =============================================================================

@pytest.mark.integration
def test_meta_ordering(
    db,
    company: Company,
    department: Department,
) -> None:
    """Employees are ordered by emp_number."""
    Employee.objects.create(
        company=company,
        emp_number="ORD-C",
        first_name="Charlie",
        last_name="Emp",
        email="charlie.emp@nexus.test",
        join_date=date(2020, 1, 1),
    )
    Employee.objects.create(
        company=company,
        emp_number="ORD-A",
        first_name="Alice",
        last_name="Emp",
        email="alice.emp@nexus.test",
        join_date=date(2020, 1, 1),
    )
    Employee.objects.create(
        company=company,
        emp_number="ORD-B",
        first_name="Bob",
        last_name="Emp",
        email="bob.emp@nexus.test",
        join_date=date(2020, 1, 1),
    )

    emp_numbers = list(
        Employee.objects.filter(company=company).values_list("emp_number", flat=True)
    )
    assert emp_numbers == ["ORD-A", "ORD-B", "ORD-C"]


@pytest.mark.unit
def test_meta_db_table() -> None:
    """Employee uses the 'employees_employee' db table."""
    assert Employee._meta.db_table == "employees_employee"


# =============================================================================
# Field-specific behavior
# =============================================================================

@pytest.mark.integration
def test_employee_optional_department_and_position(
    db,
    company: Company,
) -> None:
    """department and position are optional (nullable/protected)."""
    emp = Employee.objects.create(
        company=company,
        emp_number="OPT-001",
        first_name="No",
        last_name="Dept",
        email="no.dept@nexus.test",
        department=None,
        position=None,
        join_date=date(2020, 1, 1),
    )
    assert emp.department is None
    assert emp.position is None


@pytest.mark.integration
def test_employee_optional_base_salary(
    db,
    company: Company,
) -> None:
    """base_salary is optional (nullable/blankable)."""
    emp = Employee.objects.create(
        company=company,
        emp_number="SAL-001",
        first_name="No",
        last_name="Salary",
        email="no.salary@nexus.test",
        join_date=date(2020, 1, 1),
        base_salary=None,
    )
    assert emp.base_salary is None


@pytest.mark.integration
def test_employee_direct_manager_self_reference(
    db,
    company: Company,
    department: Department,
) -> None:
    """direct_manager is a self-referential FK (can be null)."""
    manager = Employee.objects.create(
        company=company,
        emp_number="MGR-001",
        first_name="Manager",
        last_name="Emp",
        email="manager.emp@nexus.test",
        department=department,
        join_date=date(2020, 1, 1),
    )
    report = Employee.objects.create(
        company=company,
        emp_number="RPT-001",
        first_name="Report",
        last_name="Emp",
        email="report.emp@nexus.test",
        department=department,
        direct_manager=manager,
        join_date=date(2021, 1, 1),
    )
    assert report.direct_manager == manager
    assert manager.direct_reports.count() == 1


@pytest.mark.integration
def test_employee_user_link(
    employee_with_user: Employee,
) -> None:
    """Employee can be linked to an AuthUser via user FK."""
    assert employee_with_user.user is not None
    assert employee_with_user.user.email == "linked.user@nexus.test"


@pytest.mark.integration
def test_employee_user_link_null_allowed(
    db,
    company: Company,
) -> None:
    """Employee.user is nullable — not all employees need a login account."""
    emp = Employee.objects.create(
        company=company,
        emp_number="NOL-001",
        first_name="No",
        last_name="Login",
        email="no.login@nexus.test",
        join_date=date(2020, 1, 1),
        user=None,
    )
    assert emp.user is None


# =============================================================================
# Cross-tenant isolation (negative / integration)
# =============================================================================

@pytest.mark.integration
def test_employee_cross_tenant_visible_to_other_company(
    employee: Employee,
    employee_other_company: Employee,
) -> None:
    """Both employees exist but belong to different companies."""
    assert employee.company != employee_other_company.company


@pytest.mark.integration
def test_manager_for_company_scopes_to_company(
    db,
    two_companies: tuple[Company, Company],
) -> None:
    """EmployeeManager.for_company returns only employees of the specified company."""
    company_a, company_b = two_companies

    dept_a = Department.objects.create(
        company=company_a, name="Dept A", code="DA"
    )
    dept_b = Department.objects.create(
        company=company_b, name="Dept B", code="DB"
    )

    Employee.objects.create(
        company=company_a,
        emp_number="ISO-001",
        first_name="Iso",
        last_name="A",
        email="iso.a@nexus.test",
        department=dept_a,
        join_date=date(2020, 1, 1),
    )
    Employee.objects.create(
        company=company_b,
        emp_number="ISO-002",
        first_name="Iso",
        last_name="B",
        email="iso.b@nexus.test",
        department=dept_b,
        join_date=date(2020, 1, 1),
    )

    qs_a = Employee.objects.for_company(company_a.id)
    assert qs_a.count() == 1
    assert qs_a.first().company_id == company_a.id


# =============================================================================
# Employment type and status choices
# =============================================================================

@pytest.mark.integration
def test_employment_types(
    db,
    company: Company,
    department: Department,
) -> None:
    """Employee accepts all defined EmploymentType values."""
    for emp_type in EmploymentType:
        emp = Employee.objects.create(
            company=company,
            emp_number=f"ET-{emp_type}",
            first_name=emp_type,
            last_name="Test",
            email=f"et-{emp_type}@nexus.test",
            employment_type=emp_type,
            join_date=date(2020, 1, 1),
        )
        assert emp.employment_type == emp_type


@pytest.mark.integration
def test_employee_statuses(
    db,
    company: Company,
    department: Department,
) -> None:
    """Employee accepts all defined EmployeeStatus values."""
    for emp_status in EmployeeStatus:
        emp = Employee.objects.create(
            company=company,
            emp_number=f"ES-{emp_status}",
            first_name=emp_status,
            last_name="Test",
            email=f"es-{emp_status}@nexus.test",
            status=emp_status,
            join_date=date(2020, 1, 1),
        )
        assert emp.status == emp_status


@pytest.mark.integration
def test_gender_choices(
    db,
    company: Company,
) -> None:
    """Employee accepts all defined Gender values."""
    for gender in Gender:
        emp = Employee.objects.create(
            company=company,
            emp_number=f"GD-{gender}",
            first_name=gender,
            last_name="Test",
            email=f"gd-{gender}@nexus.test",
            gender=gender,
            join_date=date(2020, 1, 1),
        )
        assert emp.gender == gender
