"""
apps/companies/constants.py

Business constants for the companies module.
Indonesian-specific values (BPJS rates, PTKP brackets) are sourced from
the nexus-domain skill and kept here so they can be referenced anywhere
in the codebase without duplication.

Attendance-specific defaults (offline sync window, leave quotas) live here
because they are tenant-policy values owned by the company layer. They are
re-exported through ``apps.attendance.constants`` so attendance code can
import them from a single, predictable location.
"""

from decimal import Decimal

# ── Default geofence ────────────────────────────────────────────────────────────
DEFAULT_GEOFENCE_RADIUS_METERS: int = 100

# ── Default employee number prefix ─────────────────────────────────────────────
DEFAULT_EMP_NUMBER_PREFIX: str = "NXS"

# ── Billing ─────────────────────────────────────────────────────────────────────
# Per-module add-on rates (Indonesian Rupiah, per active employee per month)
BILLING_RATE_CORE: Decimal = Decimal("15000")
BILLING_RATE_ATTENDANCE: Decimal = Decimal("8000")
BILLING_RATE_HSE: Decimal = Decimal("12000")
BILLING_RATE_PAYROLL: Decimal = Decimal("15000")

# ── Free tier limits ────────────────────────────────────────────────────────────
FREE_TIER_MAX_EMPLOYEES: int = 10
FREE_TIER_MAX_STORAGE_MB: int = 100

# ── Subscription plan codes ─────────────────────────────────────────────────────
PLAN_CODE_CORE: str = "core"
PLAN_CODE_ATTENDANCE: str = "attendance"
PLAN_CODE_HSE: str = "hse"
PLAN_CODE_PAYROLL: str = "full"

# ── Platform admin ──────────────────────────────────────────────────────────────
PLATFORM_ADMIN_DOMAIN: str = "platform-admin"


# ── Attendance module defaults (re-exported via apps.attendance.constants) ─────
#
# These are tenant-policy values that originate at the company layer (they
# govern how the platform treats a company's employees), so they live here.
# Attendance services/constants should import the canonical names from
# ``apps.attendance.constants`` — never from this module directly — so the
# attendance layer stays the only public surface for its own policy values.

#: Maximum age (hours) of an offline clock-in event accepted by
#: ``apps.attendance.tasks.sync_offline_attendance``. PRD offline
#: resilience window; removes the literal ``72`` from attendance code.
OFFLINE_SYNC_MAX_HOURS: int = 72

#: Statutory baseline for ``LeaveType.default_days`` and the initial
#: ``LeaveBalance.quota_days`` minted by ``initialize_leave_balances``
#: (Indonesian annual leave minimum per UU No. 13/2003, applied to
#: private-sector workers; can be overridden per LeaveType per company).
DEFAULT_ANNUAL_LEAVE_DAYS: int = 12

#: Cap applied to ``LeaveBalance.carry_over_days`` at year rollover so a
#: single employee cannot carry unlimited leave forward. Indonesian labor
#: law permits carry-over with employer agreement; this is the policy
#: ceiling enforced by the year-rollover service.
MAX_CARRY_OVER_DAYS: int = 6
