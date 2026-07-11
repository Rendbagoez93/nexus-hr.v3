# Nexus HR — GitHub Copilot Instructions

> **Companion documents** — read these before writing any code:
> - [`docs/technical-requirement-document.md`](../docs/technical-requirement-document.md) — tech stack, API design, code architecture, and testing infrastructure
> - [`docs/implementation-plan.md`](../docs/implementation-plan.md) — build order, phases, and done-when criteria
> - [`docs/implementation-steps.md`](../docs/implementation-steps.md) — step-by-step instructions for each feature implementation
> - [`docs/database-schema.md`](../docs/database-schema.md) — full database schema, table definitions, and design principles
> - [`docs/ui-ux-brief.md`](../docs/ui-ux-brief.md) — UI/UX conventions, design tokens, and component patterns
> - [`docs/PRD-overview.md`](../docs/PRD-overview.md) — product vision, personas, and domain context

---

## Project Overview

**Nexus** is a **SaaS multi-tenant HR platform** targeting manufacturing, construction, mining, and office industries in Indonesia. Centralized Employee Data Management System built on Django + DRF (web/API) and Flutter (mobile).

Four core modules: **Core** (employee master data, auth), **Attendance & Leave**, **HSE + Man Hours**, **Payroll**.

> The Employee entity is the single source of truth. Every module references it.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.14+ |
| Web Framework | Django 6.x |
| API | Django REST Framework 3.17+ |
| Auth | `djangorestframework-simplejwt` (JWT) |
| Schema / Validation | Pydantic v2 (`drf-pydantic`, `pydantic-settings`) |
| Database | PostgreSQL via `psycopg` v3 |
| File Storage | AWS S3 / MinIO via `django-storages[s3]` |
| Task Queue | Celery + Redis (`django-celery-beat`, `django-celery-results`) |
| Logging | `structlog` + `django-structlog` + `sentry-sdk` |
| Dev Tools | `pytest-django`, `factory-boy`, `ruff` |

---

## Project Structure

```
apps/
  shared/         # Cross-module utilities, mixins, logging (see technical-requirement-document.md §6)
  companies/    # Company, SubscriptionPlan, CompanySubscription
  users/        # AuthUser, RefreshToken
  attendance/     # Clock-in/out, Shifts, Leave
  hse/            # Violations, Man-hours, Work Permits, Inductions
  payroll/        # Payslips, Overtime, PPh 21, BPJS
  apis/
    v1/           # Versioned API URL routing (one sub-package per app)
config/
  settings/
    base.py
    local.py
    production.py
docs/
```

Each app follows this internal layout: `choices.py`, `constants.py`, `exceptions.py`, `managers.py`, `models.py`, `schemas.py`, `serializers.py`, `views.py`, `urls.py`, `services.py`, `admin.py`, `tests/`.

Apps are registered under the `apps/` namespace. Import as `apps.companies.models`, etc.

**Views are thin** — parse input, call a service, return a response. Business logic belongs in `services/`.

---

## Multi-Tenancy — The Most Critical Rule

**Every tenant-scoped model must inherit `TenantModel` and use `TenantManager`.**

```python
# ALWAYS use the scoped manager in views and services
Employee.objects.for_company(request.company_id)

# NEVER — raw queryset leaks cross-tenant data
Employee.objects.all()
Employee.objects.filter(...)  # without company_id scoping
```

- `TenantModel` — abstract base with `company = ForeignKey(Company, ...)`.
- `TenantManager` — exposes `.for_company(company_id)` which always appends `company_id` filtering.
- `TenantMiddleware` — extracts `company_id` from the JWT and attaches it to `request.company_id`.
- Cross-tenant access → return **403**, not 404. Never confirm or deny that a resource exists.

---

## Authentication & JWT

- `AuthUser` uses **email** as the login field, not username.
- JWT payload must contain: `user_id`, `company_id`, `role`.
- Refresh tokens are stored **hashed** (`SHA-256`) in a `RefreshToken` table — never store the raw value. Use `apps.shared.utils.security.hash_token()`.
- `RefreshToken` table is indexed on `(user_id, device_id)`.
- Platform Admin (`is_superuser=True`) accesses Django Admin only — never issued a JWT.
- Platform Admin is created via `manage.py createsuperuser` only, never through an API endpoint.

### Roles
`platform_admin` | `hr_admin` | `manager` | `employee` | `hse_officer`

---

## DRF Permission Classes

Always use the project's custom permission classes. Do not use DRF's built-in `IsAdminUser`.

| Class | Who it allows |
|---|---|
| `IsPlatformAdmin` | `is_superuser=True` only |
| `IsHRAdmin` | `hr_admin` role, same company |
| `IsManagerOrAbove` | `manager` or `hr_admin`, same company |
| `IsOwnerOrHRAdmin` | Employee accessing own record, or `hr_admin` |
| `IsHSEOfficerOrAbove` | `hse_officer`, `manager`, or `hr_admin`, same company |
| `IsEmployee` | Any authenticated employee (any role) |

---

## API Conventions

> Full endpoint catalogue, request/response shapes, and edge-case rules: [`docs/technical-requirement-document.md §3–5`](../docs/technical-requirement-document.md)

- All endpoints are prefixed `/api/v1/` — versioning is mandatory from day one.
- URL paths use **nouns, plural, kebab-case**: `/leave-requests`, not `/getLeaveRequest`.
- Maximum **two levels** of nesting: `/employees/{id}/documents` is fine; deeper paths are not.
- Use DRF `ViewSet` + `Router` for standard CRUD.
- Filterable list endpoints use `django-filter`.
- All list endpoints are **paginated** (default 25, max 100). Never return an unbounded list.
- **Never return a raw array** at the root level — wrap in `{ "count": N, "results": [...] }`.
- Validate input at the view boundary using a **Pydantic schema** — do not let raw dicts flow into services.
- Avoid N+1: use `select_related` / `prefetch_related` explicitly. Use `.only()` on read-only list endpoints.
- **Never serialize model instances directly** — use an explicit DRF serializer that maps only permitted fields.
- Cross-tenant resources return **`403`**, not `404`. Never confirm existence of another company's data.
- Critical `POST` endpoints (employee create, payroll run, disburse) require an `Idempotency-Key` header.
- Rate limiting: `10 req/min` on auth endpoints, `300 req/min` reads, `60 req/min` writes, `20 req/min` uploads.
- Standard response shapes:

**Paginated list**: `{ "count": N, "next": "...", "previous": "...", "results": [...] }`

**Single resource**: `{ "data": { "id": "uuid", ... } }`

**Action confirmation**: `{ "message": "Leave request approved successfully." }`

**Error** — always this shape (include `details` on validation errors):

```json
{
  "error": "not_found",
  "message": "Employee not found or does not belong to your company.",
  "status": 404
}
```

---

## Model Conventions

> Full field-ordering, FK rules, and constraint patterns: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md)
> Full database schema, table definitions, and design principles: [`docs/database-schema.md`](../docs/database-schema.md)

- **All PKs are UUID v4** (`UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`). Never use auto-increment integers.
- **Soft delete everywhere.** Never hard-delete tenant data. Use `SoftDeleteMixin` from `apps/shared/mixins/soft_delete.py`.
- **Money fields** use `DecimalField(max_digits=14, decimal_places=2)`. Never `FloatField` for currency.
- **Choices** are `TextChoices` classes defined in `apps/<app>/choices.py`, not inline on the field.
- **String fields**: use `blank=True, default=""` — never `null=True` on a `CharField`.
- **FKs to reference data** use `on_delete=PROTECT`; FKs to owned data use `on_delete=CASCADE`. Never use `on_delete=DO_NOTHING`.
- **Timestamps**: `created_at` / `updated_at` via `TimestampedModel` mixin from `apps/shared/mixins/timestamped.py`.
- **Required indexes** on every tenant-scoped table: `(company_id, status)` and `(company_id, employee_id)` where applicable.
- **Scoped uniqueness** via `UniqueConstraint(fields=[..., "company"])` — never a global `unique=True` on tenant fields.
- **Database invariants** (date ordering, salary min ≤ max) enforced with `CheckConstraint`, not only in Python.
- **Explicit `db_table`** in every model's `Meta` class using the `{app}_{model}` convention.
- `emp_number` auto-generates on save, unique **within** `company_id` (not globally), via `generate_emp_number()` in `apps/shared/utils/ids.py`.

---

## No Hard-Coded Values

> Full three-tier system with examples: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md)

Never inline a magic number or string in `.py` code. Use the correct tier:

| Tier | Where | What |
|------|-------|------|
| **Env vars** | `.env` → `pydantic-settings` `Settings` in `config/settings.py` | Secrets, infra URLs, token lifetimes, anything environment-specific |
| **Constants** | `apps/<app>/constants.py` | Business-rule values (BPJS rates, PTKP, geofence radius, leave quotas) |
| **Choices** | `apps/<app>/choices.py` | Valid string values for model fields (`TextChoices`) |

```python
# ❌
return min(gross, Decimal("12000000")) * Decimal("0.01")

# ✅
from apps.companies.constants import BPJS_KES_SALARY_CAP, BPJS_KES_EMPLOYEE_RATE
return min(gross, BPJS_KES_SALARY_CAP) * BPJS_KES_EMPLOYEE_RATE
```

---

## Shared Utilities

> Folder structure and full examples: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md)

**Check `apps/shared/` before writing any utility function.** If it could ever be used by more than one app, it belongs there.

Key shared modules:

| Module | Purpose |
|--------|---------|
| `apps/shared/utils/dates.py` | `get_current_utc_datetime()`, `days_until()`, `is_date_expired()` |
| `apps/shared/utils/security.py` | `hash_token()`, `generate_secure_token()`, `mask_sensitive_value()` |
| `apps/shared/utils/ids.py` | `generate_uuid()`, `generate_emp_number()` |
| `apps/shared/mixins/soft_delete.py` | `SoftDeleteMixin` |
| `apps/shared/mixins/timestamped.py` | `TimestampedModel` abstract base |
| `apps/shared/logging/logger.py` | `get_logger()`, `log_function_call()` decorator |
| `apps/shared/logging/context.py` | `bind_request_context()`, `bind_task_context()` |

Never use `datetime.utcnow()` — use `get_current_utc_datetime()` from `apps/shared/utils/dates.py`.

---

## Naming Conventions

> Full rules with examples: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md)

- **Functions**: `verb_noun` — `get_active_employees`, `calculate_monthly_overtime`, `approve_leave_request`
- **Booleans**: always `is_`, `has_`, or `can_` prefix — `is_employee_active`, `can_clock_in`
- **Variables**: specific nouns — `active_employees`, `monthly_gross`, not `e`, `mg`, `ot`
- **Classes**: `PascalCase` nouns; base/abstract classes prefixed with `Base`; Pydantic schemas suffixed with `Schema`; DRF serializers with `Serializer`
- **Constants**: `UPPER_SNAKE_CASE` in `constants.py`
- **Log events**: dot notation `resource.action` — `employee.create`, `leave_request.approve`

---

## Functions

> Full rules with examples: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md)

- **Single responsibility**: one function, one purpose. If you write "and" in the name, split it.
- **Return early**: flatten nesting with guard clauses instead of deeply nested `if` blocks.
- **Type hints are mandatory** on every parameter and return type. Use `-> None` for procedures.
- **No mutable default arguments** — use `None` and guard inside (`filters: dict | None = None`).
- Keep functions to ~30 lines. If it scrolls, look for a natural split.

---

## Queries

> Full patterns with examples: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md) and [`docs/database-schema.md`](../docs/database-schema.md)

- Always scope to company via `TenantManager`: `Employee.objects.for_company(request.company_id)` — never `.filter(company_id=...)` directly.
- Eliminate N+1 at the point of writing with `select_related` / `prefetch_related`.
- Use `.only(...)` for read-only list endpoints to avoid fetching unneeded columns.
- Use `.defer("npwp", "bank_account_number", ...)` to exclude sensitive columns from non-HR-admin queries.
- Use `.exists()` for presence checks — never `.first() is not None`.
- Wrap multi-table writes in `transaction.atomic()` at the service layer, not the view layer.
- Use `bulk_create(batch_size=500)` / `bulk_update(fields=[...], batch_size=500)` for multi-row operations — never loop `.save()` or `.create()`.
- Scope aggregations (`Sum`, `Count`, `Avg`) inside `.for_company()` — never aggregate across the full table.

---

## Logging

> Full logger module, decorator usage, and log level guide: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md)

- Use `structlog` only. No `print()`, no `logging.getLogger()`.
- Get the logger with `get_logger(__name__)` from `apps/shared/logging/logger.py`.
- Decorate every public service function with `@log_function_call("resource.action", log_args=[...])` — it auto-logs `.started`, `.succeeded`, `.failed` with duration.
- Never log raw PII (passwords, NPWP, bank account numbers). Use `mask_sensitive_value()` from `apps/shared/utils/security.py`.
- Event naming: `resource.action` for decorator prefixes; `resource.action.outcome` for manual one-off logs.

```python
from apps.shared.logging.logger import get_logger, log_function_call

log = get_logger(__name__)

@log_function_call("employee.create", log_args=["company_id"])
def create_employee(payload: EmployeeCreateSchema, company_id: uuid.UUID) -> Employee:
    ...
```

---

## Error Handling

> Full custom exception patterns: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md)

- Define custom exception classes in `apps/<app>/exceptions.py` inheriting from `NexusBaseError`.
- Never raise bare `Exception`. One custom class per distinct business failure.
- Never use bare `except`. Catch specific exception types only.
- The `@log_function_call` decorator handles `.failed` logging — do not duplicate it with a manual `log.error()` in the same function unless recording an intermediate event.

```python
class EmployeeNotFoundError(NexusBaseError):
    def __init__(self, employee_id: uuid.UUID) -> None:
        self.employee_id = employee_id
        super().__init__(f"Employee {employee_id} not found or not accessible.")
```

---

## Pydantic Schemas

> Full schema conventions and validation patterns: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md)

- Input schemas live in `apps/<app>/schemas.py`. Naming: `<Resource><Action>Schema`.
- DRF output serializers live in `apps/<app>/serializers.py`.
- Validate at the view boundary: `schema = EmployeeCreateSchema.model_validate(request.data)`.
- Never pass raw `request.data` dicts into service functions.

---

## Audit Logging

Every `POST`, `PATCH`, and `DELETE` must write to `AuditLog`:

| Field | Value |
|-------|-------|
| `table_name` | Model name |
| `record_id` | PK of the affected row |
| `action` | `create` \| `update` \| `delete` |
| `before` / `after` | JSON snapshots |
| `user_id`, `ip_address`, `timestamp` | From request context |

Hook via a Django signal or a `BaseTenantSerializer` mixin — never scatter `AuditLog.objects.create()` calls across individual views.

---

## File Storage

- Files stored on S3 with **private ACL** — never expose raw S3 URLs.
- Serve via **pre-signed URLs** (15-minute expiry).
- Never write files to the database or local disk in production.
- Local dev uses MinIO as the S3-compatible backend.

---

## Testing

> Full test types, factory conventions, and coverage requirements: [`docs/technical-requirement-document.md §7`](../docs/technical-requirement-document.md)

- Use `pytest-django` (not `unittest`). Runner config in `pyproject.toml`.
- Use `factory-boy` for all test data — no raw `Model.objects.create()` in tests except trivial cases.
- **One objective per test** — test a single behaviour. If it fails, the name alone must explain what broke.
- **Cover both paths** — every happy path must have a corresponding unhappy path (invalid input, wrong role, edge case).
- **Think like the end-user** — write tests from the perspective of an HR Admin, Manager, or Employee performing a real task.
- Tests must be **independent** — no test may rely on the state of another. Use `@pytest.fixture` for isolated setup.

### Required test categories per feature

| Category | File | What it covers |
|----------|------|----------------|
| Unit | `test_services.py` | Service functions in isolation; one outcome per test |
| API | `test_views.py` | Full HTTP cycle: status code, response shape, absent sensitive fields |
| Permission | `test_permissions.py` | Every role × action × same-company / cross-company combination |
| Tenant isolation | `test_tenant_isolation.py` | Company A token cannot read, modify, or confirm Company B data |
| Model | `test_models.py` | DB-level constraints, `__str__`, soft delete, `CheckConstraint` |
| Boundary | `test_views.py` or `test_services.py` | Pagination limits, concurrent emp_number generation, edge-case values |

### Key assertions to always include

- Cross-company access asserts exactly `403` — never `404`.
- List endpoints assert `count` and `results` keys are present.
- Sensitive fields (`npwp`, `bank_account_number`, `password`) are **absent** from list/detail responses.
- State-machine transitions (leave approval, payroll finalization) assert the transition raises an error when called twice.

---

## Tooling

| Tool | Role |
|------|------|
| `ruff` | Linting, import sorting, formatting (replaces `black` + `isort`) |
| `pyright` | Static type checking |
| `pytest` | Test runner (`--reuse-db -x` by default) |
| `pre-commit` | Runs `ruff --fix` before every commit |

Run `ruff check --fix .` and `ruff format .` before committing. Wildcard imports and unused imports are hard errors.

---

## Imports

> Full grouping rules: [`docs/technical-requirement-document.md §6`](../docs/technical-requirement-document.md)

Three groups, blank line between each, enforced by `ruff`:

```python
# 1 — Standard library
import uuid
from decimal import Decimal

# 2 — Third-party
from django.db import models, transaction
import structlog

# 3 — Internal
from apps.shared.models import TenantManager
# Employee will be in apps/employees/ — not yet created
```

No wildcard imports. No unused imports. No import aliasing unless it genuinely prevents a name clash.

---

## What NOT to Do

- Do not use `FloatField` for monetary values.
- Do not call `.objects.all()` or `.filter()` without company scoping in any view or service.
- Do not hard-delete any model referenced by historical records.
- Do not store raw refresh tokens — always hash before persisting.
- Do not expose raw S3 URLs to clients.
- Do not put Attendance, HSE, or Payroll logic in the foundational apps (`companies`, `users`, `audit`).
- Do not build features belonging to a later module (see [`docs/implementation-plan.md`](../docs/implementation-plan.md)).
- Do not use `null=True` on `CharField` — use `blank=True, default=""`.
- Do not use `datetime.utcnow()` — use `get_current_utc_datetime()`.
- Do not hard-code business values inline — use `constants.py` or `.env`.
- Do not duplicate utility logic across apps — check `apps/shared/` first.
