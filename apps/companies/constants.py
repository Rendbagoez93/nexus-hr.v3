"""
apps/companies/constants.py

Business constants for the companies module.
Indonesian-specific values (BPJS rates, PTKP brackets) are sourced from
the nexus-domain skill and kept here so they can be referenced anywhere
in the codebase without duplication.
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
