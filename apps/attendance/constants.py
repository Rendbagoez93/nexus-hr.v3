"""
apps/attendance/constants.py

All magic numbers for the attendance module live here. Values owned by the
company layer (geofence radius, offline sync window, leave quotas) are
re-exported from ``apps.companies.constants`` so they are defined in one
place. Attendance-specific policy values are defined here.

Import direction: attendance → {companies, shared}. Attendance must NOT
import employees at module top-level.
"""

from decimal import Decimal

from django.db import models

# Re-export tenant-policy values owned by the companies layer.
# Import the canonical names from here — never from apps.companies.constants
# directly — so this module is the single public surface for attendance policy.
from apps.companies.constants import (  # noqa: F401  re-exported API
    DEFAULT_ANNUAL_LEAVE_DAYS,
    DEFAULT_GEOFENCE_RADIUS_METERS,
    MAX_CARRY_OVER_DAYS,
    OFFLINE_SYNC_MAX_HOURS,
)

# ── Mobile client enforcement ───────────────────────────────────────────────────

#: Expected ``X-Client-Type`` header value from the Flutter app.
MOBILE_CLIENT_TYPE: str = "flutter-mobile"

#: HTTP header name that carries the client-type token.
CLIENT_TYPE_HEADER: str = "X-Client-Type"

# ── Attendance status derivation thresholds ──────────────────────────────────────

#: Minutes after shift start before a log is classified ``late``.
LATE_GRACE_MINUTES: int = 10

#: Worked hours at or below this value → ``half_day``.
HALF_DAY_MAX_HOURS: Decimal = Decimal("4")

#: Worked hours at or above this value → ``present`` (full day).
FULL_DAY_MIN_HOURS: Decimal = Decimal("8")

#: Rounding unit for overtime hours (quarter-hour increments).
OVERTIME_ROUNDING: Decimal = Decimal("0.25")

#: Seconds in one hour — used to convert timedelta seconds to Decimal hours
#: so all hour math stays in Decimal throughout.
SECONDS_PER_HOUR: Decimal = Decimal("3600")

# ── Leave configuration ─────────────────────────────────────────────────────────

#: Month number where the leave year starts (1 = January).
DEFAULT_LEAVE_YEAR_MONTH_START: int = 1

# ── Status TextChoices ───────────────────────────────────────────────────────────


class AttendanceStatus(models.TextChoices):
    """Derived daily attendance status, written by ``compute_daily_attendance_status``."""

    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"
    LATE = "late", "Late"
    HALF_DAY = "half_day", "Half Day"
    ON_LEAVE = "on_leave", "On Leave"
    PENDING = "pending", "Pending"


class LeaveStatus(models.TextChoices):
    """Lifecycle of a leave request."""

    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class DisputeStatus(models.TextChoices):
    """Lifecycle of an attendance dispute raised by an employee."""

    OPEN = "open", "Open"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class SiteStatus(models.TextChoices):
    """Lifecycle of a site (geofence-bound location)."""

    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class ProjectStatus(models.TextChoices):
    """Lifecycle of a project (organizational grouping on top of a site)."""

    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


# ── Pagination ─────────────────────────────────────────────────────────────────

#: Default page size for attendance log list endpoints.
ATTENDANCE_LOG_PAGE_SIZE: int = 25
