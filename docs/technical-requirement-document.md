# Technical Requirement Document — Nexus HR

**Version**: 1.2 | **Date**: July 2026 | **Status**: Active Development

---

## 1. Tech Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | ≥ 3.14 |
| Web Framework | Django | ≥ 6.0.5 |
| REST API | Django REST Framework | ≥ 3.17.1 |
| Authentication | djangorestframework-simplejwt | ≥ 5.5.1 |
| Schema Validation | Pydantic + drf-pydantic | ≥ 2.13.4 / ≥ 2.9.1 |
| Database | PostgreSQL (via psycopg) | ≥ 3.3.4 |
| Task Queue | Celery + Redis | ≥ 5.6 / ≥ 5.0 |
| Task Scheduling | django-celery-beat | ≥ 2.7 |
| Task Results | django-celery-results | ≥ 2.5 |
| File Storage | django-storages (S3) | ≥ 1.14 |
| Filtering | django-filter | ≥ 25.2 |
| Structured Logging | structlog + django-structlog | ≥ 25.5 / ≥ 10.0 |
| Error Monitoring | sentry-sdk (Django) | ≥ 2.20 |
| Settings Management | pydantic-settings | ≥ 2.14.1 |

### Dev / Testing Tools

| Tool | Purpose |
|------|---------|
| pytest-django | Test runner |
| factory-boy | Test data factories |
| django-debug-toolbar | Local development debugging |
| black | Code formatting |
| ruff | Linting + import sorting + formatting |

### Frontend

| Component | Technology |
|-----------|-----------|
| Template Engine | Django Templates |
| CSS | Vanilla CSS with custom properties (design tokens) |
| JavaScript | Vanilla JS (no framework) |
| Typeface | Inter (Google Fonts, weights 300–800) |
| Layout | CSS Grid (multi-column) + Flexbox (single-axis) |

### Mobile (Planned)

| Component | Technology |
|-----------|-----------|
| Framework | Flutter |
| Capability | Offline-first clock-in/out with auto-sync |

---

## 2. Infrastructure

### Environment Configuration

All secrets and environment-specific values managed via `pydantic-settings` reading from `.env`: SECRET_KEY, DATABASE_URL, REDIS_URL, DEBUG, ALLOWED_HOSTS, AWS_BUCKET_NAME, AWS_REGION, AWS_SIGNED_URL_EXPIRY_SECONDS, ACCESS_TOKEN_LIFETIME_MINUTES, REFRESH_TOKEN_LIFETIME_DAYS, SENTRY_DSN, SENTRY_ENVIRONMENT 

### Settings Architecture

- config/settings/
- base.py ← shared settings
- local.py ← DEBUG=True, console email backend
- production.py ← DEBUG=False, real SMTP, Sentry enabled
- envcommon.py ← environment-common settings

### Storage

- **Database**: PostgreSQL
- **File Storage**: S3-compatible (MinIO for local dev, AWS S3 for production)
- **Cache / Broker**: Redis
- **Static Files**: Django `collectstatic` → `staticfiles/`

---

## 3. API Design

### Base URL & Versioning

```text
https://{host}/api/v1/{resource}
```

Breaking changes introduce `/api/v2/` while maintaining `/api/v1/` in parallel.

### URL Structure Rules

| Rule | Correct | Incorrect |
|------|---------|-----------|
| Nouns, not verbs | `GET /employees` | `GET /getEmployees` |
| Pluralise all collections | `GET /employees/42` | `GET /employee/42` |
| kebab-case for multi-word paths | `/leave-requests` | `/leaveRequests` |
| Maximum two levels of nesting | `/employees/{id}/documents` | `/employees/{id}/departments/{id}/positions` |
| Query params to filter | `/employees?department_id=X` | `/departments/X/employees/active` |
| Actions use sub-path noun | `POST /leave-requests/{id}/approve` | `POST /approveLeaveRequest` |

### Authentication

- Bearer JWT in `Authorization` header (except `/auth/login` and `/auth/token/refresh`)
- JWT payload: `user_id`, `company_id`, `role`
- `TenantMiddleware` reads `company_id` from token → attaches to `request.company_id`

### Rate Limiting

| Tier | Limit |
|------|-------|
| Auth endpoints (`/auth/*`) | 10 req/min per IP |
| Standard read endpoints | 300 req/min per token |
| Write endpoints | 60 req/min per token |
| File upload endpoints | 20 req/min per token |

### Idempotency

POST endpoints that mutate durable state accept `Idempotency-Key` header (UUID v4). Keys expire after 24 hours. Required on: `POST /employees`, `POST /leave-requests`, `POST /payroll-runs`, `POST /payslips/{id}/disburse`.

### Response Envelope

**Paginated list:**

```json
{ "count": 150, "next": "...", "previous": "...", "results": [{...}] }
```

**Single resource:**

```json
{ "data": { "id": "uuid", ... } }
```

**Action confirmation:**

```json
{ "message": "Leave request approved successfully." }
```

### Pagination

Default page size: 25, Maximum: 100  
`page_size > 100` → 400 error

### HTTP Status Codes

| Situation | Code |
|-----------|------|
| Successful read | 200 |
| Resource created | 201 |
| Action completed, no body | 204 |
| Validation failed | 400 |
| Missing/invalid JWT | 401 |
| Insufficient role / wrong company | 403 |
| Cross-tenant resource | 403 (never 404) |
| Resource not found | 404 |
| Conflict | 409 |
| Rate limit exceeded | 429 |
| Server error | 500 |

### Error Response Shape

```json
{
  "error": "validation_error",
  "message": "join_date must not be in the future.",
  "status": 400,
  "details": { "join_date": ["This field may not be in the future."] }
}
```

---

## 4. API Endpoints

### Module: Core

#### Auth

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| POST | `/api/v1/auth/login` | Exchange email + password for tokens | Public |
| POST | `/api/v1/auth/token/refresh` | Refresh access token | Public |
| POST | `/api/v1/auth/logout` | Revoke refresh token | Authenticated |
| POST | `/api/v1/auth/password/change` | Change own password | Authenticated |

#### Departments

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/departments` | List active departments | IsHRAdmin |
| POST | `/api/v1/departments` | Create department | IsHRAdmin |
| GET | `/api/v1/departments/{id}` | Retrieve department | IsHRAdmin |
| PATCH | `/api/v1/departments/{id}` | Update department | IsHRAdmin |
| DELETE | `/api/v1/departments/{id}` | Soft-delete department | IsHRAdmin |

#### Positions

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/positions` | List positions | IsHRAdmin |
| POST | `/api/v1/positions` | Create position | IsHRAdmin |
| GET | `/api/v1/positions/{id}` | Retrieve position | IsHRAdmin |
| PATCH | `/api/v1/positions/{id}` | Update position | IsHRAdmin |
| DELETE | `/api/v1/positions/{id}` | Soft-delete position | IsHRAdmin |

#### Employees

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/employees` | List employees (paginated) | IsHRAdmin |
| POST | `/api/v1/employees` | Create employee (+ optional login) | IsHRAdmin |
| GET | `/api/v1/employees/{id}` | Retrieve employee detail | IsOwnerOrHRAdmin |
| PATCH | `/api/v1/employees/{id}` | Update employee | IsHRAdmin |
| POST | `/api/v1/employees/{id}/deactivate` | Deactivate employee | IsHRAdmin |
| GET | `/api/v1/me` | Retrieve own profile | Authenticated |

#### Employee Documents

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/employees/{id}/documents` | List documents | IsOwnerOrHRAdmin |
| POST | `/api/v1/employees/{id}/documents` | Upload document | IsHRAdmin |
| GET | `/api/v1/employees/{id}/documents/{doc_id}` | Get document + signed URL | IsOwnerOrHRAdmin |
| PATCH | `/api/v1/employees/{id}/documents/{doc_id}` | Update metadata | IsHRAdmin |
| DELETE | `/api/v1/employees/{id}/documents/{doc_id}` | Soft-delete document | IsHRAdmin |

### Module: Attendance & Leave

#### Attendance Logs

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/attendance-logs` | List logs (paginated) | IsManagerOrAbove |
| GET | `/api/v1/attendance-logs/{id}` | Retrieve log | IsOwnerOrHRAdmin |
| POST | `/api/v1/attendance-logs/clock-in` | Submit clock-in | IsEmployee |
| POST | `/api/v1/attendance-logs/clock-out` | Submit clock-out | IsEmployee |
| PATCH | `/api/v1/attendance-logs/{id}` | Attendance correction | IsHRAdmin |

#### Shifts

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET/POST | `/api/v1/shifts` | List / Create | IsHRAdmin |
| GET/PATCH/DELETE | `/api/v1/shifts/{id}` | Retrieve / Update / Soft-delete | IsHRAdmin |

#### Leave Types

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET/POST | `/api/v1/leave-types` | List / Create | IsHRAdmin |
| GET/PATCH/DELETE | `/api/v1/leave-types/{id}` | Retrieve / Update / Soft-delete | IsHRAdmin |

#### Leave Requests

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/leave-requests` | List (paginated) | IsManagerOrAbove |
| POST | `/api/v1/leave-requests` | Submit request | Authenticated |
| GET | `/api/v1/leave-requests/{id}` | Retrieve | IsOwnerOrHRAdmin |
| PATCH | `/api/v1/leave-requests/{id}` | Edit pending | IsOwner |
| DELETE | `/api/v1/leave-requests/{id}` | Cancel pending | IsOwner |
| POST | `/api/v1/leave-requests/{id}/approve` | Approve | IsManagerOrAbove |
| POST | `/api/v1/leave-requests/{id}/reject` | Reject with reason | IsManagerOrAbove |

#### Leave Balances

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/leave-balances` | List all balances | IsHRAdmin |
| GET | `/api/v1/leave-balances/{employee_id}` | Get employee balances | IsOwnerOrHRAdmin |
### Module: HSE + Man Hours

#### Safety Violations

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET/POST | `/api/v1/violations` | List / Report | IsHSEOfficerOrAbove |
| GET/PATCH | `/api/v1/violations/{id}` | Retrieve / Update | IsHSEOfficerOrAbove |

#### Man Hours (read-only, derived by Celery)

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/man-hours` | List man-hours | IsHSEOfficerOrAbove |
| GET | `/api/v1/man-hours/summary` | Aggregated totals | IsHSEOfficerOrAbove |

#### Inductions

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET/POST | `/api/v1/inductions` | List / Record | IsHSEOfficerOrAbove |
| GET/PATCH | `/api/v1/inductions/{id}` | Retrieve / Update | IsHSEOfficerOrAbove |

#### Work Permits

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET/POST | `/api/v1/work-permits` | List / Create | IsHSEOfficerOrAbove |
| GET/PATCH | `/api/v1/work-permits/{id}` | Retrieve / Update | IsHSEOfficerOrAbove |
| POST | `/api/v1/work-permits/{id}/approve` | Approve | IsHRAdmin / HSE Lead |
| POST | `/api/v1/work-permits/{id}/close` | Close | IsHSEOfficerOrAbove |

### Module: Payroll

#### Payroll Runs

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET/POST | `/api/v1/payroll-runs` | List / Initiate | IsHRAdmin |
| GET | `/api/v1/payroll-runs/{id}` | Retrieve detail | IsHRAdmin |
| POST | `/api/v1/payroll-runs/{id}/finalize` | Lock run | IsHRAdmin |
| POST | `/api/v1/payroll-runs/{id}/cancel` | Cancel draft | IsHRAdmin |

#### Payslips

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/payslips` | List (paginated) | IsHRAdmin |
| GET | `/api/v1/payslips/{id}` | Retrieve detail | IsOwnerOrHRAdmin |
| GET | `/api/v1/payslips/{id}/download` | Signed PDF URL | IsOwnerOrHRAdmin |
| POST | `/api/v1/payslips/{id}/disburse` | Mark disbursed | IsHRAdmin |

#### Notifications (Future — Schema Reserved)

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/api/v1/notifications` | List own notifications | Authenticated |
| POST | `/api/v1/notifications/{id}/read` | Mark as read | IsOwner |
| POST | `/api/v1/notifications/read-all` | Mark all as read | Authenticated |

## 5. OpenAPI / Schema-First Workflow

1. Draft the OpenAPI schema first
2. Review schema (request/response shapes, error cases)
3. Implement the DRF view (serializer must match schema)
4. Validate with drf-spectacular

Schema files: `docs/openapi/` (one per module: `core.yaml`, `attendance.yaml`, `hse.yaml`, `payroll.yaml`)

## 6. Code Architecture

### Project Structure

```text
apps/
  shared/           ← cross-module utilities, mixins, permissions, logging, utils
  core/             ← Company, AuthUser, Employee, Department, Position, Documents
    models/         ← company.py, department.py, position.py, employee.py, document.py, audit.py
    selectors/      ← read queries
    services/       ← write logic / business rules
    serializers/    ← internal serializers (not API layer)
    views_web.py    ← Django views for HTMX dashboard (thin)
    urls_web.py     ← HTMX dashboard URL routing
    admin.py
    choices.py
    constants.py
    exceptions.py
    managers.py
    tests/
  attendance/       ← AttendanceLog, Shift, LeaveType, LeaveRequest, LeaveBalance
    models/
    selectors/
    services/
    serializers/
    views_web.py
    urls_web.py
    admin.py
    choices.py
    constants.py
    exceptions.py
    managers.py
    tests/
  hse/              ← Violation, ManHours, Induction, WorkPermit
    models/
    selectors/
    services/
    serializers/
    views_web.py
    urls_web.py
    admin.py
    choices.py
    constants.py
    exceptions.py
    managers.py
    tests/
  payroll/           ← PayrollRun, Payslip, PayslipComponent
    models/
    selectors/
    services/
    serializers/
    views_web.py
    urls_web.py
    admin.py
    choices.py
    constants.py
    exceptions.py
    managers.py
    tests/
  apis/              ← centralized API layer
    v1/
      __init__.py
      core/
        views.py     ← DRF viewsets/views
        urls.py      ← API URL routing
      attendance/
        views.py
        urls.py
      hse/
        views.py
        urls.py
      payroll/
        views.py
        urls.py
      schemas/        ← OpenAPI schemas per module
        core.yaml
        attendance.yaml
        hse.yaml
        payroll.yaml
      serializers/   ← API request/response serializers
        core.py
        attendance.py
        hse.py
        payroll.py
      routers.py     ← DRF DefaultRouter registering all ViewSets
      urls.py        ← root API URL configuration (includes all sub-routers)
config/
  settings/         ← base.py, local.py, production.py
  urls.py
  wsgi.py / asgi.py
```

### Per Module Structure (apps/{module}/)

Each functional module under `apps/` follows this internal structure:

```text
apps/{module}/
  __init__.py
  apps.py           ← Django app config
  admin.py
  choices.py        ← TextChoices classes
  constants.py      ← business-rule constants
  exceptions.py     ← custom exception classes
  managers.py       ← TenantManager / custom QuerySets
  models.py         ← or models/ directory for larger modules
  selectors.py      ← read queries
  services.py       ← write logic / business rules
  serializers.py    ← internal serializers (not API layer)
  views_web.py      ← Django views for HTMX dashboard (thin)
  urls_web.py       ← HTMX dashboard URL routing
  tests/            ← test_models, test_services, test_permissions
```

### Per API Module Structure (apps/apis/v1/{module}/)

API views and URLs live under `apps/apis/v1/<module>/`, separate from the Django app:

```text
apps/apis/v1/{module}/
  __init__.py
  views.py          ← DRF viewsets/views (thin — call services/selectors)
  urls.py           ← API URL routing for this module
```

Each API module calls selectors and services from its corresponding Django app. The API layer is intentionally decoupled from the internal module structure, keeping the API contract stable even if internal implementation changes.

### Multi-Tenancy Architecture

- TenantModel abstract base → adds company FK + TenantManager
- TenantManager.for_company(company_id) → explicit tenant scoping
- TenantMiddleware → reads company_id from JWT → request.company_id
- All views/services must call .for_company() — never naked .objects

### Permission Classes

| Class | Description |
|-------|-------------|
| IsPlatformAdmin | is_superuser=True only |
| IsHRAdmin | role hr_admin within same company |
| IsManagerOrAbove | role manager, hr_admin |
| IsOwnerOrHRAdmin | employee accessing own record, or HR Admin |
| IsHSEOfficerOrAbove | HSE officer or higher roles |
| IsEmployee | Any authenticated employee |

### View Pattern: CBV vs FBV

- **CBV/ViewSets** for the resource-shaped modules (Core, Attendance, HSE, Payroll) — use DRF `ModelViewSet`/`GenericAPIView` + `@action` for sub-path actions (`approve`, `reject`, `finalize`, `cancel`, `disburse`, `clock-in`, `clock-out`), registered via router.
- **FBV** for the handful of non-resource utility endpoints — `auth/login`, `auth/token/refresh`, `auth/logout`, `auth/password/change`, `/me`, `man-hours/summary`.
- Either way, the `views.py` thin-views rule above still applies — no business logic in the view, CBV or FBV.

## 7. Testing Infrastructure

### Tools

| Tool | Role |
|------|------|
| pytest-django | Test runner |
| factory-boy | Test data factories |
| APIClient (DRF) | HTTP layer testing |
| freezegun | Time-sensitive tests |
| pytest-cov | Coverage reporting |
| pytest-xdist | Parallel test execution |

### Coverage Requirements

| App | Minimum |
|-----|----------|
| core | 85% |
| attendance | 80% |
| hse | 80% |
| payroll | 85% |
| shared | 90% |

### Test Categories

- **Unit Tests** — service functions in isolation
- **API Tests** — full HTTP request/response cycle
- **Permission Tests** — every role × action × company combination
- **Tenant Isolation Tests** — cross-company data protection
- **Model Tests** — constraints, computed properties
- **Authentication Tests** — login, logout, token refresh, platform admin restrictions
- **Boundary Tests** — pagination limits, concurrent creates, year boundaries
- **Negative Tests** — invalid input, malformed payloads, denied permissions, business-rule violations (e.g. double-disbursement, expired induction used for site access, invalid PTKP config, cross-company resource ID guessing)

### Test Categorization & Markers

Every test belongs to exactly one of three top-level categories, declared with a custom pytest marker so the suite can be filtered, staged in CI, and reported on independently. The categories above are not replaced — each one rolls up into one of the three markers:

| Marker | Category | Scope | Rolls up from |
|--------|----------|-------|----------------|
| `@pytest.mark.unit` | **Unit Test** | Single function/class, no DB or network I/O, no Django test client | Model Tests (pure logic/computed properties), service-layer unit tests |
| `@pytest.mark.integration` | **Integration Test** | Multiple components together (DB, services, Celery tasks, managers) without going through HTTP | Tenant Isolation Tests, Boundary Tests, man-hours aggregation / payroll calculation pipelines |
| `@pytest.mark.feature` | **Feature Test** | Full HTTP request/response cycle via DRF `APIClient`, simulating real user behavior end-to-end | API Tests, Permission Tests, Authentication Tests |

Negative Tests are not a fourth marker — a negative test takes whichever marker matches the layer it exercises (e.g. invalid PTKP config at the service layer → `integration`; denied-permission or malformed-payload at the endpoint layer → `feature`).

Rules:
- Markers are registered explicitly in `pyproject.toml` under `[tool.pytest.ini_options]` (`markers = [...]`) so an unregistered/misspelled marker fails the run rather than being silently ignored.
- Exactly one of the three markers is required per test — no unmarked tests, no test carrying more than one.
- Every write endpoint (`POST`/`PUT`/`PATCH`/`DELETE`) must ship with at least one negative-path test alongside its happy-path test — denied permission, invalid payload, or business-rule violation. A PR adding a write endpoint without a negative case fails review.
- CI runs the markers as separate stages: `unit` (fastest, every push) → `integration` (every PR) → `feature` (every PR, plus full nightly run). A failing `unit` stage blocks `integration`/`feature` from running.
- Per-module coverage targets (above) are measured across all three categories combined, not per category.

```python
@pytest.mark.unit
def test_pph21_gross_up_calculation():
    ...

@pytest.mark.integration
def test_man_hours_aggregation_from_attendance_logs():
    ...

@pytest.mark.feature
def test_leave_request_approval_flow(api_client, hr_admin_user):
    ...
```

### Fixture Scope Optimization

Fixture scope is chosen per data type to cut redundant setup cost without leaking mutated state between tests:

| Scope | Use for | Example |
|-------|---------|---------|
| `session` | Expensive, read-only, shared for the entire run | Test DB connection/migrations, MinIO/S3 test bucket bootstrap |
| `module` | Reference/lookup data reused across one test file, never mutated by a test | `company`, `department`, `leave_type` factories used read-only within a file |
| `class` | Shared setup for a grouped set of tests, reset between classes | One company + one role fixture per permission-test class |
| `function` (default) | Anything created, mutated, or asserted on within a single test | `employee`, `attendance_log`, `payroll_run` instances |

Rule: a fixture may be widened beyond `function` scope only if no test mutates the object it returns. If a wider-scoped fixture needs a per-test variation, override it with a `function`-scoped fixture that clones/copies the base object instead of mutating the shared instance — this keeps `unit`/`integration` tests fast while `feature` tests (which more often need fresh per-test state) stay isolated.
