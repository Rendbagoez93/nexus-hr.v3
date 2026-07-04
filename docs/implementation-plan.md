# Implementation Plan — Nexus HR

**Version**: 1.2 | **Date**: July 2026 | **Status**: Active Development

> ⚠️ **NOTE**: Detailed build order exists only for the **Core module** (Phases 1–8).
> Attendance, HSE, and Payroll module build orders are **not yet documented**.
> Their phases below are inferred from dependency analysis and API design.

---

## Guiding Principle

> **"No employee, no system."**
> The Core module is the foundation every other module is built on top of. The Employee entity is the single source of truth. Build in dependency order.

---

## Phase 1 — Project Scaffold & Tenant Infrastructure

**Build this before anything else.**

### Tasks

- [ ] Django project structure with app separation: `apps/core`, `apps/attendance`, `apps/hse`, `apps/payroll`
- [ ] `apps/shared/` with cross-module utilities:
  - `utils/dates.py` — `get_current_utc_datetime()`, `get_current_date()`, `days_until()`, `is_date_expired()`
  - `utils/ids.py` — `generate_uuid()`, `generate_emp_number()`
  - `utils/security.py` — `hash_token()`, `generate_secure_token()`, `mask_sensitive_value()`
  - `mixins/soft_delete.py` — `SoftDeleteMixin` with `is_active` + `deleted_at` + `deactivate()`
  - `mixins/timestamped.py` — `TimestampedModel` abstract base
  - `logging/logger.py` — `get_logger()`, `log_function_call()` decorator
  - `logging/context.py` — `bind_request_context()`, `bind_task_context()`
- [ ] `TenantModel` — abstract base model with `company` FK + `TenantManager`
- [ ] `TenantManager` — custom ORM manager with `.for_company(company_id)` method
- [ ] `TenantMiddleware` — attaches `request.company_id` from JWT
- [ ] Base settings split: `settings/base.py`, `settings/local.py`, `settings/production.py`
- [ ] PostgreSQL connection configured
- [ ] `pydantic-settings` for environment/secrets management
- [ ] `structlog` + `django-structlog` configured

### Done When

- `TenantModel` has `company = ForeignKey(Company, ...)` and uses `TenantManager`
- `TenantMiddleware` injects `request.company_id` correctly
- A test proves tenant-scoped querying works

---

## Phase 2 — Company

**The tenant boundary. Everything else is a child of Company.**

### Tasks

- [ ] `Company` model — name, industry, subscription tier, active flag, geofence fields, timestamps
- [ ] `SubscriptionPlan` model — `has_attendance`, `has_hse`, `has_payroll` flags
- [ ] `CompanySubscription` model — links company to plan, billing period, active employee count
- [ ] Django Admin registration for all three models
- [ ] `apps/core/constants.py` — all business constants (BPJS rates, PTKP values, etc.)
- [ ] `apps/core/choices.py` — all TextChoices classes

### Done When

- Platform Admin can create a Company via Django Admin
- `CompanySubscription` correctly reflects enabled modules
- New Company has clean slate (no users, no employees)

---

## Phase 3 — Auth & AuthUser

**Identity layer. Every person starts here.**

### Tasks

- [ ] Custom `AuthUser` model extending `AbstractBaseUser` — email login, role field, company FK
- [ ] Role choices: `platform_admin`, `hr_admin`, `manager`, `employee`, `hse_officer`
- [ ] JWT authentication via `djangorestframework-simplejwt`
  - Access token: short-lived (60 min)
  - Refresh token: long-lived (30 days)
- [ ] `RefreshToken` model — `token_hash`, `expires_at`, `device_id`, `is_revoked`
- [ ] `POST /api/v1/auth/login` — exchange email + password for tokens
- [ ] `POST /api/v1/auth/token/refresh` — refresh access token
- [ ] `POST /api/v1/auth/logout` — revoke refresh token
- [ ] `POST /api/v1/auth/password/change` — change own password
- [ ] `LoginSchema` in `apps/core/schemas.py`
- [ ] Auth service in `apps/core/services/auth.py`
- [ ] `TenantMiddleware` update: extract `company_id` from JWT payload
- [ ] Platform Admin: created via `manage.py createsuperuser` only — never JWT for HR dashboard

### Done When

- HR Admin can log in and receive JWT
- JWT contains `user_id`, `company_id`, `role`
- Logout invalidates refresh token
- Cross-company token test passes

---

## Phase 4 — Department

**Org-chart structure.**

### Tasks

- [ ] `Department` model — name, code, company FK, parent self-FK, soft delete
- [ ] CRUD API (HR Admin only):
  - `GET /api/v1/departments` — list with optional `parent_id`, `is_active` filters
  - `POST /api/v1/departments`
  - `GET /api/v1/departments/{id}`
  - `PATCH /api/v1/departments/{id}`
  - `DELETE /api/v1/departments/{id}` — soft delete
- [ ] Department service in `apps/core/services/department.py`
- [ ] Serializer with nested children for org-chart
- [ ] `DepartmentCreateSchema`, `DepartmentUpdateSchema`

### Done When

- HR Admin can create department tree (parent → child)
- List returns only requesting company's departments
- Cross-company isolation verified

---

## Phase 5 — Position

**Job titles with salary bands.**

### Tasks

- [ ] `Position` model — title, level, department FK, company FK, salary min/max, soft delete
- [ ] CRUD API (HR Admin only):
  - `GET /api/v1/positions` — list with `department_id`, `level` filters
  - `POST /api/v1/positions`
  - `GET /api/v1/positions/{id}`
  - `PATCH /api/v1/positions/{id}`
  - `DELETE /api/v1/positions/{id}` — soft delete
- [ ] Position service in `apps/core/services/position.py`
- [ ] `select_related("department")` to avoid N+1

### Done When

- Positions scoped to company
- Salary fields use Decimal
- Filterable by department

---

## Phase 6 — Employee

**The central entity.**

### Tasks

- [ ] `Employee` model — full personal, employment, compliance fields
- [ ] O2O link to `AuthUser` (nullable)
- [ ] Employee status lifecycle: active, inactive, resigned, terminated
- [ ] CRUD API (HR Admin):
  - `GET /api/v1/employees` — paginated, filterable
  - `POST /api/v1/employees` — create + optional AuthUser creation
  - `GET /api/v1/employees/{id}` — detail
  - `PATCH /api/v1/employees/{id}` — update
  - `POST /api/v1/employees/{id}/deactivate` — change status + resign_date
- [ ] Self-service: `GET /api/v1/me`
- [ ] `EmployeeCreateSchema`, `EmployeeUpdateSchema`
- [ ] Employee service in `apps/core/services/employee_service.py`
- [ ] Auto-generated `emp_number` (NXS-0001 format, unique per company)
- [ ] `transaction.atomic()` for employee + user + leave balance creation

### Done When

- Create employee with optional login in one API call
- `GET /api/v1/me` returns own record
- Filtering works, all results company-scoped
- `emp_number` auto-generates correctly

---

## Phase 7 — Employee Document

**File attachments per employee.**

### Tasks

- [ ] `EmployeeDocument` model — employee FK, doc_type, file_url, valid_until, is_verified
- [ ] API endpoints:
  - `POST /api/v1/employees/{id}/documents` — upload
  - `GET /api/v1/employees/{id}/documents` — list
  - `GET /api/v1/employees/{id}/documents/{doc_id}` — signed URL
  - `PATCH /api/v1/employees/{id}/documents/{doc_id}` — update metadata
  - `DELETE /api/v1/employees/{id}/documents/{doc_id}` — soft delete
- [ ] S3 storage integration (MinIO local, AWS S3 production)
- [ ] Signed URL generation with 15-minute expiry
- [ ] Private ACL on all files

### Done When

- File uploaded and retrieved via signed URL
- Documents scoped to employee → company
- Expired signed URLs return 403

---

## Phase 8 — API Layer & Permissions

**Harden what you've built.**

### Tasks

- [ ] DRF Permission classes:
  - `IsPlatformAdmin`
  - `IsHRAdmin`
  - `IsManagerOrAbove`
  - `IsOwnerOrHRAdmin`
  - `IsHSEOfficerOrAbove`
  - `IsEmployee`
- [ ] `apps/shared/permissions.py`
- [ ] Standardized API error response format
- [ ] `AuditLog` model — append-only, before/after JSON snapshots
- [ ] Auto-hook AuditLog via Django signal or base serializer mixin
- [ ] `Notification` model — table created for schema stability
- [ ] Custom exception classes in `apps/core/exceptions.py`
- [ ] `apps/shared/exceptions.py` — `NexusBaseError`
- [ ] Shared pagination class in `apps/shared/utils/pagination.py`

### Done When

- Cross-company access returns 403 (not 404)
- Every POST/PATCH/DELETE recorded in AuditLog
- Permission classes tested for all role combinations

---

## Phase 9 — Attendance Module

> ⚠️ Build order not formally documented. Inferred sequence below.

### Tasks

- [ ] `Shift` model + CRUD API
- [ ] `AttendanceLog` model
- [ ] Clock-in service with GPS geofencing validation
- [ ] Clock-out service with photo verification
- [ ] Offline sync validation (72h window)
- [ ] `POST /api/v1/attendance-logs/clock-in`
- [ ] `POST /api/v1/attendance-logs/clock-out`
- [ ] Attendance correction endpoint
- [ ] `LeaveType` model + CRUD API
- [ ] `LeaveRequest` model + full workflow (submit → approve/reject → balance deduction)
- [ ] `LeaveBalance` model + initialization on employee creation
- [ ] Leave API: submit, approve, reject, cancel, list, balances
- [ ] Attendance status derivation (present, absent, late, half_day)
- [ ] Celery task for daily attendance status computation

### Done When

- Employee can clock in/out from mobile with GPS validation
- Offline sync works within 72h
- Leave request workflow complete with balance tracking
- Tenant isolation tests pass

---

## Phase 10 — HSE Module

> ⚠️ Build order not formally documented. Inferred sequence below.

### Tasks

- [ ] `Violation` model + CRUD API
- [ ] `ManHours` model (read-only from API)
- [ ] Celery task for man-hours aggregation from attendance logs
- [ ] Man-hours summary endpoint
- [ ] `Induction` model + CRUD API
- [ ] Induction expiry alerts (Celery periodic task, 14 days before)
- [ ] `WorkPermit` model + full lifecycle API
- [ ] Work permit approval workflow (draft → pending → approved → active → closed → expired)

### Done When

- Violations reportable with severity and status lifecycle
- Man-hours aggregated correctly from attendance
- Inductions trackable with expiry alerts
- Work permits follow multi-step approval

---

## Phase 11 — Payroll Module

> ⚠️ Build order not formally documented. Inferred sequence below.

### Tasks

- [ ] `PayrollRun` model + API
- [ ] `Payslip` model + component breakdown
- [ ] BPJS Ketenagakerjaan calculation service
- [ ] BPJS Kesehatan calculation service (with Rp 12M cap)
- [ ] PPh 21 calculation service (gross-up for permanent, nett for contract)
- [ ] Payroll run initiation → Celery background calculation
- [ ] Payslip generation for all active employees
- [ ] Payroll run finalization (lock)
- [ ] Payslip PDF generation + signed URL download
- [ ] Disbursement recording
- [ ] Idempotency protection on payroll runs

### Done When

- Payroll run calculates all components correctly
- BPJS and PPh 21 match Indonesian regulations
- Finalized runs are immutable
- Payslips downloadable as PDF

---

## Phase 12 — Landing Page & Frontend

### Tasks

- [ ] `base.html` template with nav, footer, script tags
- [ ] `index.html` landing page with hero, features, industries, stats, compliance, CTA, footer
- [ ] `index.css` with full design token system
- [ ] `index.js` with scroll reveal, counters, nav scroll state, smooth scroll
- [ ] Responsive breakpoints (1024px, 768px, 480px)

---

## Testing Strategy (All Phases)

For every phase, write tests in parallel:

| Test File | Coverage |
|-----------|----------|
| `test_models.py` | Model constraints, `__str__`, computed properties |
| `test_services.py` | Service function unit tests (mock only external I/O) |
| `test_views.py` | API endpoint tests (HTTP in, HTTP out) |
| `test_permissions.py` | Every role × action × company combination |
| `test_tenant_isolation.py` | Cross-company data protection |

### Coverage Requirements

| App | Minimum |
|-----|---------|
| core | 85% |
| attendance | 80% |
| hse | 80% |
| payroll | 85% |
| shared | 90% |

### Testing Rules

- Use `factory-boy` factories — never `Model.objects.create()` in tests
- Assert exact status codes — never `response.ok`
- Assert `403` for cross-tenant — never `404`
- Use `freezegun` for date-sensitive tests
- Mock only external I/O (S3, email, Celery) — never mock the database

---

## Definition of Done — Full System

- [ ] All Core module phases (1–8) complete and tested
- [ ] Attendance module complete with clock-in/out, shifts, leave
- [ ] HSE module complete with violations, man-hours, inductions, work permits
- [ ] Payroll module complete with BPJS, PPh 21, payslip generation
- [ ] Cross-company isolation tested for every module
- [ ] Landing page built per design system
- [ ] All API endpoints match OpenAPI schemas
- [ ] Coverage requirements met for all apps
- [ ] Structured logging on every service function
- [ ] No raw `.objects.all()` calls in views
