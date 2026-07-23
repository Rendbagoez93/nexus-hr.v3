"""
apps/attendance/selectors.py

Read-only query layer for the attendance module.

All selectors take an explicit ``company_id`` as first argument and scope through
``Model.objects.for_company(company_id)``. No selector returns cross-tenant rows.
Soft-deleted rows are filtered via ``.alive()`` unless ``include_deleted=True`` is
passed.

Tenant scoping is enforced ONLY here. Services call selectors and must never
build raw querysets directly.

Import direction: attendance → {companies, shared, employees (string FK only)}.
Attendance must NOT import ``employees`` at module top-level.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from django.db.models import Q, QuerySet

if TYPE_CHECKING:
    from apps.attendance.models import (
        AttendanceDispute,
        AttendanceLog,
        LeaveBalance,
        LeaveRequest,
        LeaveType,
        Project,
        Shift,
        ShiftAssignment,
        Site,
        SiteAssignment,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shifts
# ─────────────────────────────────────────────────────────────────────────────


def list_shifts(
    company_id: UUID,
    *,
    include_inactive: bool = False,
) -> QuerySet[Shift]:
    """
    List all shifts for a company.

    By default returns only active (non-deleted) shifts. Pass
    ``include_inactive=True`` to include soft-deleted rows.
    """
    qs = Shift.objects.for_company(company_id)
    if not include_inactive:
        qs = qs.alive()
    return qs


def get_shift(company_id: UUID, shift_id: UUID) -> Shift:
    """
    Fetch a single shift by ID, scoped to the company.

    Raises
    ------
    Shift.DoesNotExist
        If the shift does not exist or belongs to another company.
    """
    return Shift.objects.for_company(company_id).get(pk=shift_id)


def get_active_shift_assignment(
    company_id: UUID,
    employee_id: UUID,
    on_date: date,
) -> ShiftAssignment | None:
    """
    Return the currently-active shift assignment for an employee on a given date.

    An assignment is active when ``effective_from <= on_date`` and
    ``effective_until IS NULL OR effective_until >= on_date``.

    Returns None if the employee has no shift assignment for that date.
    """
    return (
        ShiftAssignment.objects.for_company(company_id)
        .filter(
            employee_id=employee_id,
            effective_from__lte=on_date,
        )
        .filter(
            Q(effective_until__isnull=True)
            | Q(effective_until__gte=on_date)
        )
        .select_related("shift")
        .first()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Attendance logs
# ─────────────────────────────────────────────────────────────────────────────


def list_attendance_logs(
    company_id: UUID,
    *,
    employee_id: UUID | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[AttendanceLog]:
    """
    List attendance logs for a company with optional filters.

    Parameters
    ----------
    employee_id
        Filter to a specific employee's logs.
    status
        Filter by attendance status value (e.g. ``present``, ``absent``).
    date_from / date_to
        Filter to a date range (inclusive).
    """
    qs = AttendanceLog.objects.for_company(company_id)
    if employee_id is not None:
        qs = qs.filter(employee_id=employee_id)
    if status is not None:
        qs = qs.filter(status=status)
    if date_from is not None:
        qs = qs.filter(work_date__gte=date_from)
    if date_to is not None:
        qs = qs.filter(work_date__lte=date_to)
    return qs.select_related("employee", "shift", "site")


def get_attendance_log(company_id: UUID, log_id: UUID) -> AttendanceLog:
    """
    Fetch a single attendance log by ID, scoped to the company.

    Raises
    ------
    AttendanceLog.DoesNotExist
        If the log does not exist or belongs to another company.
    """
    return AttendanceLog.objects.for_company(company_id).select_related(
        "employee", "shift", "site"
    ).get(pk=log_id)


def get_open_log_for_today(
    company_id: UUID,
    employee_id: UUID,
    work_date: date,
) -> AttendanceLog | None:
    """
    Return the open (un-clocked-out) attendance log for an employee on a date.

    Returns None if no open log exists for the given date.
    """
    return (
        AttendanceLog.objects.for_company(company_id)
        .filter(
            employee_id=employee_id,
            work_date=work_date,
            clock_in_at__isnull=False,
            clock_out_at__isnull=True,
        )
        .select_related("shift", "site")
        .first()
    )


def list_team_attendance(
    company_id: UUID,
    manager_employee_id: UUID,
    *,
    work_date: date | None = None,
) -> QuerySet[AttendanceLog]:
    """
    List attendance logs for employees whose direct manager is ``manager_employee_id``.

    Optionally filter to a specific ``work_date``.
    """
    qs = AttendanceLog.objects.for_company(company_id).filter(
        employee__direct_manager_id=manager_employee_id
    )
    if work_date is not None:
        qs = qs.filter(work_date=work_date)
    return qs.select_related("employee", "shift", "site")


# ─────────────────────────────────────────────────────────────────────────────
# Leave types
# ─────────────────────────────────────────────────────────────────────────────


def list_leave_types(
    company_id: UUID,
    *,
    include_inactive: bool = False,
) -> QuerySet[LeaveType]:
    """
    List all leave types for a company.

    By default returns only active (non-deleted) leave types.
    """
    qs = LeaveType.objects.for_company(company_id)
    if not include_inactive:
        qs = qs.alive()
    return qs


# ─────────────────────────────────────────────────────────────────────────────
# Leave requests
# ─────────────────────────────────────────────────────────────────────────────


def list_leave_requests(
    company_id: UUID,
    *,
    employee_id: UUID | None = None,
    status: str | None = None,
) -> QuerySet[LeaveRequest]:
    """
    List leave requests for a company with optional filters.

    Parameters
    ----------
    employee_id
        Filter to a specific employee's requests.
    status
        Filter by leave status value (e.g. ``pending``, ``approved``).
    """
    qs = LeaveRequest.objects.for_company(company_id)
    if employee_id is not None:
        qs = qs.filter(employee_id=employee_id)
    if status is not None:
        qs = qs.filter(status=status)
    return qs.select_related("employee", "leave_type", "approved_by")


def get_leave_request(company_id: UUID, request_id: UUID) -> LeaveRequest:
    """
    Fetch a single leave request by ID, scoped to the company.

    Raises
    ------
    LeaveRequest.DoesNotExist
        If the request does not exist or belongs to another company.
    """
    return LeaveRequest.objects.for_company(company_id).select_related(
        "employee", "leave_type", "approved_by"
    ).get(pk=request_id)


# ─────────────────────────────────────────────────────────────────────────────
# Leave balances
# ─────────────────────────────────────────────────────────────────────────────


def get_leave_balance(
    company_id: UUID,
    employee_id: UUID,
    *,
    leave_type_id: UUID | None = None,
    year: int | None = None,
) -> QuerySet[LeaveBalance]:
    """
    Fetch leave balance(s) for an employee.

    Returns a QuerySet so callers can fetch one row or iterate. When both
    ``leave_type_id`` and ``year`` are provided the QuerySet will contain at
    most one row.

    Parameters
    ----------
    leave_type_id
        Filter to a specific leave type.
    year
        Filter to a specific leave year.
    """
    qs = LeaveBalance.objects.for_company(company_id).filter(
        employee_id=employee_id
    )
    if leave_type_id is not None:
        qs = qs.filter(leave_type_id=leave_type_id)
    if year is not None:
        qs = qs.filter(year=year)
    return qs.select_related("employee", "leave_type")


def list_leave_balances(
    company_id: UUID,
    *,
    year: int | None = None,
) -> QuerySet[LeaveBalance]:
    """
    List all leave balances for a company (HR-wide view).

    Optionally filter to a specific leave ``year``.
    """
    qs = LeaveBalance.objects.for_company(company_id)
    if year is not None:
        qs = qs.filter(year=year)
    return qs.select_related("employee", "leave_type")


# ─────────────────────────────────────────────────────────────────────────────
# Sites & projects
# ─────────────────────────────────────────────────────────────────────────────


def get_active_site_assignment(
    company_id: UUID,
    employee_id: UUID,
    on_date: date,
) -> SiteAssignment | None:
    """
    Return the currently-active site assignment for an employee on a given date.

    Used by the geofence validator to resolve whether a site-specific geofence
    should be applied at clock-in.
    """
    return (
        SiteAssignment.objects.for_company(company_id)
        .filter(
            employee_id=employee_id,
            effective_from__lte=on_date,
        )
        .filter(
            Q(effective_until__isnull=True)
            | Q(effective_until__gte=on_date)
        )
        .select_related("site")
        .first()
    )


def list_sites(
    company_id: UUID,
    *,
    status: str | None = None,
) -> QuerySet[Site]:
    """
    List all sites for a company.

    Optionally filter by status (e.g. ``active``).
    """
    qs = Site.objects.for_company(company_id)
    if status is not None:
        qs = qs.filter(status=status)
    return qs


def get_site(company_id: UUID, site_id: UUID) -> Site:
    """
    Fetch a single site by ID, scoped to the company.

    Raises
    ------
    Site.DoesNotExist
        If the site does not exist or belongs to another company.
    """
    return Site.objects.for_company(company_id).get(pk=site_id)


def list_projects(company_id: UUID) -> QuerySet[Project]:
    """List all projects for a company."""
    return Project.objects.for_company(company_id).select_related("site")


# ─────────────────────────────────────────────────────────────────────────────
# Disputes
# ─────────────────────────────────────────────────────────────────────────────


def list_disputes(
    company_id: UUID,
    *,
    status: str | None = None,
) -> QuerySet[AttendanceDispute]:
    """
    List attendance disputes for a company.

    Optionally filter by status (e.g. ``open``).
    """
    qs = AttendanceDispute.objects.for_company(company_id)
    if status is not None:
        qs = qs.filter(status=status)
    return qs.select_related("attendance_log", "raised_by", "resolved_by")


def get_dispute(company_id: UUID, dispute_id: UUID) -> AttendanceDispute:
    """
    Fetch a single dispute by ID, scoped to the company.

    Raises
    ------
    AttendanceDispute.DoesNotExist
        If the dispute does not exist or belongs to another company.
    """
    return AttendanceDispute.objects.for_company(company_id).select_related(
        "attendance_log", "raised_by", "resolved_by"
    ).get(pk=dispute_id)
