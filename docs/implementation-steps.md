# Implementation Steps — Nexus HR

**Version**: 1.2 | **Date**: July 4, 2026 | **Status**: Active Development

> This document is the **developer-facing build guide**. It organizes every
> implementation task from `implementation-plan.md` into four sequential tracks:
> Configuration, Modules, API, and Templates. Work each track in the order
> listed. The Guiding Principle remains: **no employee, no system** — build in
> dependency order.

---

## 1. Configuration Implementation Steps

Set up the project scaffold, infrastructure, and shared utilities before any
module code is written.

### 1.1 — Project Scaffold

- [ ] Create Django project `nexus_hr` at the repo root
- [ ] Create top-level directory structure:
  ```
  nexus-hr.v2/
  ├── config/
  │   └── settings/       ← base.py, local.py, production.py, envcommon.py
  ├── apps/
  │   ├── shared/         ← cross-module utilities
  │   ├── core/           ← Company, AuthUser, Employee, Department, Position
  │   ├── attendance/     ← Attendance, Shift, Leave
  │   ├── hse/            ← Violation, ManHours, Induction, WorkPermit
  │   └── payroll/        ← PayrollRun, Payslip
  ├── templates/
  ├── static/
  ├── tests/
  └── docs/
  ```
- [ ] Add `apps/` to `sys.path` or configure as a Django app directory

### 1.2 — Settings Architecture

- [ ] Create `config/settings/base.py` — shared settings (installed apps, DB, cache, logging)
- [ ] Create `config/settings/local.py` — `DEBUG=True`, console email backend, file-based media
- [ ] Create `config/settings/production.py` — `DEBUG=False`, SMTP, S3 storage, Sentry
- [ ] Create `config/settings/envcommon.py` — environment-common settings consumed by pydantic-settings
- [ ] Create root `config/settings.py` (or `config/__init__.py`) that imports from the correct environment
- [ ] Install and configure `pydantic-settings` — all secrets from `.env` (SECRET_KEY, DATABASE_URL, REDIS_URL, AWS_BUCKET_NAME, etc.)
- [ ] Configure PostgreSQL connection in base.py
- [ ] Configure Redis / Celery in base.py

### 1.3 — Shared Utilities (`apps/shared/`)

Create these before any module, since every module depends on them.

**Utils (`apps/shared/utils/`)**
- [ ] `dates.py` — `get_current_utc_datetime()`, `get_current_date()`, `days_until()`, `is_date_expired()`
- [ ] `ids.py` — `generate_uuid()`, `generate_emp_number()`
- [ ] `security.py` — `hash_token()`, `generate_secure_token()`, `mask_sensitive_value()`
- [ ] `pagination.py` — shared `NexusPaginator` class (default 25, max 100)

**Mixins (`apps/shared/mixins/`)**
- [ ] `soft_delete.py` — `SoftDeleteMixin`: `is_active` flag + `deleted_at` + `deactivate()` method
- [ ] `timestamped.py` — `TimestampedModel`: `created_at` + `updated_at` auto fields

**Logging (`apps/shared/logging/`)**
- [ ] `logger.py` — `get_logger()`, `log_function_call()` decorator
- [ ] `context.py` — `bind_request_context()`, `bind_task_context()`
- [ ] Configure `structlog` + `django-structlog` in settings

**Permissions (`apps/shared/permissions.py`)**
- [ ] `IsPlatformAdmin` — `is_superuser=True` only
- [ ] `IsHRAdmin` — role `hr_admin` within same company
- [ ] `IsManagerOrAbove` — role `manager` or `hr_admin`
- [ ] `IsOwnerOrHRAdmin` — employee accessing own record, or HR Admin
- [ ] `IsHSEOfficerOrAbove` — HSE officer or higher roles
- [ ] `IsEmployee` — any authenticated employee
- [ ] `HasModuleAccess(module_flag)` — subscription-tier gating factory

**Exceptions (`apps/shared/exceptions.py`)**
- [ ] `NexusBaseError` — base exception
- [ ] `NexusNotFound`, `NexusForbidden`, `NexusValidationError`, `NexusConflict`

### 1.4 — Tenant Infrastructure

- [ ] Create `TenantModel` abstract base model with `company = ForeignKey(Company)` and `TenantManager`
- [ ] Create `TenantManager` with `.for_company(company_id)` method — all tenant-scoped queries must use this
- [ ] Create `TenantMiddleware` — extracts `company_id` from JWT payload, attaches to `request.company_id`
- [ ] Add `company_id` to JWT token payload (see Auth setup in §2.3)
- [ ] Write a test proving tenant-scoped querying works (two companies, verify isolation)

### 1.5 — S3 Storage Configuration

- [ ] Install and configure `django-storages` with S3 backend
- [ ] Set `AWS_S3_ENDPOINT_URL` for MinIO (local dev) and AWS S3 (production)
- [ ] Configure private ACL and signed URL generation (15-minute expiry)
- [ ] Create storage helper in `apps/shared/utils/storage.py` — `upload_file()`, `generate_signed_url()`, `delete_file()`

### 1.6 — Celery + Background Tasks Setup

- [ ] Configure Celery with Redis broker in `config/celery.py`
- [ ] Create `apps/shared/tasks.py` — base Celery task class with structured logging
- [ ] Register Celery app in Django settings
- [ ] Configure `django-celery-beat` for periodic tasks
- [ ] Configure `django-celery-results` for task result storage

---

## 2. Modules Implementation Steps

Build modules in dependency order: Core first, then Attendance, then HSE, then Payroll.

### 2.1 — Core Module — Company & Subscription

**Models (`apps/core/models/company.py`)**
- [ ] `Company` — name, industry, subscription_tier, is_active, geofence fields, timestamps
- [ ] `SubscriptionPlan` — name, has_attendance, has_hse, has_payroll flags
- [ ] `CompanySubscription` — links company to plan, billing_period, active_employee_count
- [ ] Register all three in `apps/core/admin.py`

**Constants & Choices (`apps/core/`)**
- [ ] `constants.py` — all business constants: BPJS rates, PTKP values, leave quotas, geofence radius, offline sync window
- [ ] `choices.py` — all TextChoices classes: industry, subscription_tier, employment_type, employee_status, document types, etc.

**Selectors (`apps/core/selectors/company.py`)**
- [ ] `get_company_by_id(company_id)` — returns company or raises NexusNotFound
- [ ] `list_companies()` — platform admin only
- [ ] `get_company_subscription(company)` — returns active subscription with plan details

### 2.2 — Core Module — Auth & AuthUser

**Model (`apps/core/models/user.py`)**
- [ ] `AuthUser` extending `AbstractBaseUser` — email as login field, role, company FK (nullable for platform admin), timestamps
- [ ] Role choices: `platform_admin`, `hr_admin`, `manager`, `employee`, `hse_officer`
- [ ] `RefreshToken` model — token_hash, expires_at, device_id, is_revoked (indexed on user_id + device_id, user_id + is_revoked)

**Services (`apps/core/services/auth.py`)**
- [ ] `authenticate_user(email, password)` — validates credentials, returns user or None
- [ ] `create_tokens_for_user(user)` — generates access + refresh tokens
- [ ] `refresh_access_token(refresh_token)` — validates and returns new access token
- [ ] `revoke_refresh_token(token_hash)` — marks token as revoked
- [ ] `revoke_all_user_tokens(user)` — revoke all refresh tokens for user (used on password reset)
- [ ] `change_password(user, old_password, new_password)` — validates old, sets new
- [ ] `send_password_reset_email(email)` — sends reset email (always returns success to avoid email enumeration)

**JWT Configuration**
- [ ] Configure `djangorestframework-simplejwt` — access token 60 min, refresh token 30 days
- [ ] Add `user_id`, `company_id`, `role` to JWT payload
- [ ] Update `TenantMiddleware` to read `company_id` from JWT

**API Endpoints**
- [ ] `POST /api/v1/auth/login` — exchange email + password for tokens
- [ ] `POST /api/v1/auth/token/refresh` — refresh access token
- [ ] `POST /api/v1/auth/logout` — revoke refresh token
- [ ] `POST /api/v1/auth/password/change` — change own password
- [ ] `POST /api/v1/auth/password/reset` — request password reset email

**Done when**: HR Admin can log in and receive JWT containing user_id, company_id, role. Cross-company token test passes.

### 2.3 — Core Module — Department

**Model (`apps/core/models/department.py`)**
- [ ] `Department` — name, code, company FK, parent self-FK, is_active, deleted_at, timestamps
- [ ] Unique constraint on (company, code)
- [ ] Index on (company_id, is_active), (company_id, parent_id)

**Selectors (`apps/core/selectors/department.py`)**
- [ ] `list_departments(company_id, parent_id=None, is_active=True)` — tenant-scoped list
- [ ] `get_department_tree(company_id)` — returns nested tree for org-chart display
- [ ] `get_department_by_id(department_id, company_id)` — raises NexusNotFound if not found or wrong company

**Services (`apps/core/services/department.py`)**
- [ ] `create_department(company_id, data)` — creates department, validates code uniqueness
- [ ] `update_department(department_id, company_id, data)` — updates fields
- [ ] `soft_delete_department(department_id, company_id)` — sets is_active=False

**Serializers (`apps/core/serializers/department.py`)**
- [ ] `DepartmentSerializer` — output serializer with nested children
- [ ] `DepartmentCreateSerializer`, `DepartmentUpdateSerializer` — input validation

**Views (`apps/core/views_api.py`)**
- [ ] `DepartmentViewSet` — CRUD via DRF ModelViewSet, thin views calling selectors/services

**URLs (`apps/core/urls_api.py`)**
- [ ] Register Department routes: `/api/v1/departments`

### 2.4 — Core Module — Position

**Model (`apps/core/models/position.py`)**
- [ ] `Position` — title, level, department FK, company FK, base_salary_min/max (DecimalField), is_active, deleted_at, timestamps
- [ ] Check constraint: base_salary_min <= base_salary_max

**Selectors (`apps/core/selectors/position.py`)**
- [ ] `list_positions(company_id, department_id=None, level=None, is_active=True)`
- [ ] `get_position_by_id(position_id, company_id)`

**Services (`apps/core/services/position.py`)**
- [ ] `create_position(company_id, data)`
- [ ] `update_position(position_id, company_id, data)`
- [ ] `soft_delete_position(position_id, company_id)`

**Serializers (`apps/core/serializers/position.py`)**
- [ ] `PositionSerializer`, `PositionCreateSerializer`, `PositionUpdateSerializer`

**Views + URLs**
- [ ] `PositionViewSet` — CRUD, registered at `/api/v1/positions`

### 2.5 — Core Module — Employee

**Model (`apps/core/models/employee.py`)**
- [ ] `Employee` — full personal, employment, and compliance fields as per database-schema.md
- [ ] O2O link to `AuthUser` (nullable)
- [ ] Auto-generated `emp_number` (NXS-0001 format, unique per company)
- [ ] Employee status lifecycle: active, inactive, resigned, terminated
- [ ] Indexes: (company_id, status), (company_id, department_id), (company_id, employment_type)
- [ ] Unique constraint on (company, emp_number)

**Selectors (`apps/core/selectors/employee.py`)**
- [ ] `list_employees(company_id, filters)` — paginated, filterable by department, status, position, employment_type
- [ ] `get_employee_by_id(employee_id, company_id)`
- [ ] `get_employee_by_user_id(user_id)`
- [ ] `get_employee_by_emp_number(emp_number, company_id)`
- [ ] `count_active_employees(company_id)` — for subscription billing

**Services (`apps/core/services/employee_service.py`)**
- [ ] `create_employee(company_id, data, create_user=False)` — `transaction.atomic()` for employee + optional user creation
- [ ] `update_employee(employee_id, company_id, data)`
- [ ] `deactivate_employee(employee_id, company_id, status, resign_date)` — changes status + sets resign_date
- [ ] `generate_emp_number(company_id)` — NXS-0001 format, thread-safe

**Serializers (`apps/core/serializers/employee.py`)**
- [ ] `EmployeeListSerializer`, `EmployeeDetailSerializer`, `EmployeeCreateSerializer`, `EmployeeUpdateSerializer`

**Views + URLs**
- [ ] `EmployeeViewSet` — CRUD + `/me` action + `/deactivate` action
- [ ] Registered at `/api/v1/employees`

### 2.6 — Core Module — Employee Document

**Model (`apps/core/models/document.py`)**
- [ ] `EmployeeDocument` — employee FK, doc_type, file_url (S3 key), file_name, valid_until, is_verified, is_active, deleted_at, timestamps

**Services (`apps/core/services/document_service.py`)**
- [ ] `upload_employee_document(employee_id, company_id, doc_type, file, file_name, valid_until)` — stores to S3, creates record
- [ ] `get_document_signed_url(document_id, company_id)` — generates 15-min signed URL
- [ ] `update_document_metadata(document_id, company_id, data)`
- [ ] `soft_delete_document(document_id, company_id)`

**Serializers (`apps/core/serializers/document.py`)**
- [ ] `DocumentSerializer`, `DocumentCreateSerializer`

**Views + URLs**
- [ ] Document endpoints nested under employee: `/api/v1/employees/{id}/documents/`

### 2.7 — Core Module — Audit & Notifications

**Audit (`apps/core/models/audit.py`)**
- [ ] `AuditLog` — append-only, stores table_name, record_id, action, before/after JSON, user_id, ip_address, timestamp
- [ ] Hook into Django's `post_save` and `post_delete` signals for automatic logging
- [ ] Create signal handler in `apps/core/signals.py`

**Notifications (`apps/core/models/notification.py`)**
- [ ] `Notification` model — user FK, title, message, is_read, created_at (schema reserved for future)

### 2.8 — Attendance Module

**Models (`apps/attendance/models/`)**
- [ ] `Shift` — name, start_time, end_time, is_active, deleted_at, timestamps
- [ ] `ShiftAssignment` — employee FK, shift FK, effective_from, effective_until (for rotating assignments)
- [ ] `AttendanceLog` — employee FK, work_date, clock_in_at, clock_out_at, GPS fields, photo fields, shift FK, status, is_offline_sync, total_overtime_hours, timestamps
- [ ] `LeaveType` — name, default_days, carry_over_allowed, is_active, deleted_at, timestamps
- [ ] `LeaveRequest` — employee FK, leave_type FK, start_date, end_date, reason, status, approved_by FK, decided_at, rejection_reason, timestamps
- [ ] `LeaveBalance` — employee FK, leave_type FK, year, quota_days, used_days, carry_over_days, timestamps

**Shift Selectors/Services**
- [ ] `list_shifts(company_id)`, `create_shift(company_id, data)`, `update_shift()`, `soft_delete_shift()`
- [ ] `assign_shift_to_employee(employee_id, shift_id, effective_from, effective_until)` — auto-closes prior assignment

**Attendance Selectors/Services**
- [ ] `clock_in(employee_id, company_id, data)` — validates GPS geofence, stores photo, creates log
- [ ] `clock_out(employee_id, company_id, data)` — pairs with most recent clock-in, calculates overtime
- [ ] `get_attendance_log(log_id, company_id)` — detail view
- [ ] `list_attendance_logs(company_id, filters)` — paginated, filterable
- [ ] `correct_attendance(log_id, company_id, data)` — HR admin correction

**Leave Selectors/Services**
- [ ] `initialize_leave_balances(employee_id, company_id)` — called on employee creation
- [ ] `submit_leave_request(employee_id, company_id, data)` — creates request with status pending
- [ ] `approve_leave_request(request_id, approver_id, company_id)` — sets status=approved, deducts balance
- [ ] `reject_leave_request(request_id, approver_id, company_id, reason)` — sets status=rejected
- [ ] `cancel_leave_request(request_id, employee_id)` — employee cancels pending request, restores balance
- [ ] `list_leave_requests(company_id, filters)`, `get_leave_balance(employee_id, year)`

**Celery Tasks**
- [ ] `compute_daily_attendance_status` — runs end of day, derives present/absent/late/half_day status
- [ ] `sync_offline_attendance` — processes offline clock-in records within 72h window

**Views + URLs**
- [ ] `AttendanceLogViewSet` — CRUD + `/clock-in`, `/clock-out`, `/correct` actions at `/api/v1/attendance-logs`
- [ ] `ShiftViewSet` at `/api/v1/shifts`
- [ ] `LeaveTypeViewSet` at `/api/v1/leave-types`
- [ ] `LeaveRequestViewSet` at `/api/v1/leave-requests` — with `/approve`, `/reject`, `/cancel` sub-path actions
- [ ] `LeaveBalanceViewSet` at `/api/v1/leave-balances`

### 2.9 — HSE Module

**Models (`apps/hse/models/`)**
- [ ] `Violation` — employee FK, severity, status, description, photo_url, incident_date, reported_by FK, resolved_at, timestamps
- [ ] `ManHours` — employee FK, period_year, period_month, hours_worked, overtime_hours (read-only, derived)
- [ ] `Induction` — employee FK, induction_type, completed_date, valid_until, is_verified, certificate_url, timestamps
- [ ] `WorkPermit` — permit_type, status, description, location, requested_by FK, approved_by FK, start_date, end_date, safety_checklist JSONField, timestamps

**Violation Selectors/Services**
- [ ] `report_violation(company_id, data)` — creates violation with status open
- [ ] `update_violation_status(violation_id, company_id, status, notes)` — transitions open → in_review → resolved

**ManHours Selectors/Services**
- [ ] `get_man_hours_summary(company_id, period_year, period_month)` — aggregated totals by department/project
- [ ] `get_employee_man_hours(employee_id, period_year, period_month)`

**Celery Tasks**
- [ ] `aggregate_man_hours` — runs periodically, aggregates attendance logs into ManHours records
- [ ] `check_induction_expiry` — runs daily, alerts 14 days before expiry
- [ ] `check_work_permit_expiry` — marks expired permits, alerts HSE officer

**Induction Selectors/Services**
- [ ] `record_induction(company_id, data)`, `update_induction()`, `list_inductions(company_id, filters)`

**WorkPermit Selectors/Services**
- [ ] `create_work_permit(company_id, data)` — status draft
- [ ] `submit_work_permit(permit_id, company_id)` — draft → pending_approval
- [ ] `hse_officer_review(permit_id, company_id, approved, notes)` — pending_approval → approved or rejected
- [ ] `manager_final_approval(permit_id, company_id, approved, notes)` — approved → active or rejected
- [ ] `close_work_permit(permit_id, company_id)` — active → closed
- [ ] `list_work_permits(company_id, filters)`

**Views + URLs**
- [ ] `ViolationViewSet` at `/api/v1/violations`
- [ ] `ManHoursViewSet` at `/api/v1/man-hours` — read-only
- [ ] `InductionViewSet` at `/api/v1/inductions`
- [ ] `WorkPermitViewSet` at `/api/v1/work-permits` — with `/approve`, `/close` actions

### 2.10 — Payroll Module

**Models (`apps/payroll/models/`)**
- [ ] `PayrollRun` — period_year, period_month, status, notes, initiated_by FK, finalized_at, timestamps
- [ ] `Payslip` — employee FK, payroll_run FK, period_year, period_month, all salary/deduction components (all DecimalField), status, disbursement_ref, disbursed_at, timestamps
- [ ] Unique constraint: (company, employee, period_year, period_month) on Payslip
- [ ] Unique constraint: (company, period_year, period_month) WHERE status IN (draft, processing, finalized) on PayrollRun

**BPJS Services (`apps/payroll/services/bpjs.py`)**
- [ ] `calculate_bpjs_tk_employee(gross_salary)` — 2% of gross, capped at salary cap
- [ ] `calculate_bpjs_tk_company(gross_salary)` — 3.7% of gross, capped at salary cap
- [ ] `calculate_bpjs_kes_employee(gross_salary)` — 1% of gross, capped at Rp 12,000,000
- [ ] `calculate_bpjs_kes_company(gross_salary)` — 4% of gross, capped at Rp 12,000,000

**PPh 21 Service (`apps/payroll/services/pph21.py`)**
- [ ] `calculate_pph21_gross_up(annual_gross, tax_status)` — UU HPP No. 7/2021 gross-up formula
- [ ] `calculate_pph21_nett(annual_nett, tax_status)` — for contract employees
- [ ] `calculate_annual_gross_salary(monthly_base, allowances, overtime, benefits)` — builds PTKP-eligible gross
- [ ] `calculate_monthly_pph21(annual_pph21)` — divide annual by 12

**Payroll Run Service (`apps/payroll/services/payroll_service.py`)**
- [ ] `initiate_payroll_run(company_id, period_year, period_month, user_id, idempotency_key)` — creates draft run, queues Celery task
- [ ] `calculate_payslips_for_run(run_id)` — Celery task: loops active employees, calculates each payslip
- [ ] `finalize_payroll_run(run_id, company_id)` — locks run, prevents further edits
- [ ] `cancel_payroll_run(run_id, company_id)` — cancels draft run
- [ ] `disburse_payslip(payslip_id, company_id, disbursement_ref)` — marks disbursed

**Celery Tasks**
- [ ] `process_payroll_run` — background payroll calculation per employee
- [ ] `generate_payslip_pdf` — generates PDF for a payslip

**Selectors**
- [ ] `get_payroll_run(run_id, company_id)`, `list_payroll_runs(company_id, filters)`
- [ ] `get_payslip(payslip_id, company_id)`, `list_payslips(company_id, filters)`

**Views + URLs**
- [ ] `PayrollRunViewSet` at `/api/v1/payroll-runs` — with `/finalize`, `/cancel` actions
- [ ] `PayslipViewSet` at `/api/v1/payslips` — with `/download`, `/disburse` actions

---

## 3. API Implementation Steps

Implement after all modules are complete. This section covers cross-cutting API infrastructure, not module-specific endpoints (those are in §2).

### 3.1 — OpenAPI Schema Setup

- [ ] Install and configure `drf-spectacular` in settings
- [ ] Create `docs/openapi/` directory
- [ ] Draft `docs/openapi/core.yaml` — all Core module endpoints
- [ ] Draft `docs/openapi/attendance.yaml` — all Attendance module endpoints
- [ ] Draft `docs/openapi/hse.yaml` — all HSE module endpoints
- [ ] Draft `docs/openapi/payroll.yaml` — all Payroll module endpoints
- [ ] Register schemas in DRF settings: `DEFAULT_SCHEMA_CLASS = 'drf_spectacular.utils.views.AutoSchema'`
- [ ] Validate all serializers against schemas using `drf-spectacular`

### 3.2 — API Router Configuration

- [ ] Create `apps/apis/v1/urls.py` — root URL configuration
- [ ] Create `apps/apis/v1/routers.py` — DRF DefaultRouter registering all ViewSets
- [ ] Mount router at `/api/v1/`
- [ ] Configure root `/api/v1/` to return API metadata (version, description)

### 3.3 — Standardized Response Envelope

- [ ] Create `apps/shared/utils/response.py` — `StandardResponse` class:
  - Paginated list: `{ "count": N, "next": "...", "previous": "...", "results": [...] }`
  - Single resource: `{ "data": { ... } }`
  - Action confirmation: `{ "message": "..." }`
  - Error: `{ "error": "...", "message": "...", "status": N, "details": {...} }`
- [ ] Override DRF `ExceptionHandler` to use standardized error shape

### 3.4 — Idempotency

- [ ] Create `apps/shared/middleware/idempotency.py` middleware
- [ ] Idempotency-Key header (UUID v4) accepted on POST endpoints
- [ ] Keys stored in Redis with 24-hour TTL
- [ ] Required endpoints: `/employees`, `/leave-requests`, `/payroll-runs`, `/payslips/{id}/disburse`

### 3.5 — Rate Limiting

- [ ] Configure DRF throttling classes:
  - `AnonThrottle` — 10 req/min per IP for auth endpoints
  - `UserReadThrottle` — 300 req/min per token for reads
  - `UserWriteThrottle` — 60 req/min per token for writes
  - `UserUploadThrottle` — 20 req/min per token for uploads
- [ ] Apply `throttle_classes` at the viewset level, not globally

### 3.6 — API Tests

For each module, write the following tests:

- [ ] `test_auth_login_success` — valid credentials return tokens
- [ ] `test_auth_login_failure` — invalid credentials return 401
- [ ] `test_auth_logout_revokes_token` — revoked token cannot refresh
- [ ] `test_tenant_isolation` — company A cannot access company B resources (returns 403, not 404)
- [ ] `test_permission_hr_admin` — hr_admin can CRUD their company's resources
- [ ] `test_permission_manager` — manager can read but not write beyond scope
- [ ] `test_permission_employee` — employee can only access own record and clock-in/out
- [ ] `test_pagination_limit` — page_size > 100 returns 400
- [ ] `test_idempotency_key_replay` — same key on duplicate POST returns original response
- [ ] `test_create_validation_error` — invalid input returns 400 with details
- [ ] `test_not_found_returns_404` — valid UUID not in company returns 404
- [ ] `test_cross_company_returns_403` — resource from other company returns 403

---

## 4. Templates Implementation Steps

Build the web dashboard (Django Templates + HTMX) after API endpoints are complete. The dashboard is server-rendered with HTMX for partial updates — no SPA framework.

### 4.1 — Base Template & Static Assets

**Base Template (`templates/base.html`)**
- [ ] Load `static` tag as first line
- [ ] HTML shell: `<!DOCTYPE html>`, `<html lang="en">`, `<head>` with meta tags
- [ ] Include design token CSS via `<link rel="stylesheet" href="{% static 'css/tokens.css' %}">`
- [ ] Include component CSS via `<link rel="stylesheet" href="{% static 'css/components.css' %}">`
- [ ] Fixed topbar: company name, user name + role badge, notification bell, user menu
- [ ] Sidebar: role-filtered navigation per sidebar structure (§1.2 in user-journey-flow.md)
- [ ] Main content area: `{% block content %}{% endblock %}`
- [ ] Breadcrumb: derived from URL path
- [ ] `<script>` tags at end of `<body>`: htmx.js, app.js
- [ ] `{% block extra_css %}{% endblock %}`, `{% block extra_js %}{% endblock %}`

**Design Tokens CSS (`static/css/tokens.css`)**
- [ ] `:root` block with all CSS custom properties from ui-ux-brief.md:
  - `--color-bg`, `--color-bg-card-2`, `--color-bg-card`
  - `--color-primary`, `--color-primary-dk`, `--color-primary-lt`, `--color-accent`
  - `--color-success`, `--color-warning`, `--color-danger`
  - `--color-text`, `--color-text-muted`, `--color-text-subtle`
  - `--color-border`
  - `--shadow-card`, `--shadow-glow`
  - `--radius-sm`, `--radius-md`, `--radius-lg`
  - All spacing tokens: `--space-2xs` through `--space-4xl`
  - All typography tokens

**Component CSS (`static/css/components.css`)**
- [ ] Tag pill component
- [ ] Button variants: `.btn-primary`, `.btn-ghost`, `.btn-outline` with all sizes
- [ ] Card component with hover gradient effect
- [ ] Status badge component
- [ ] Form inputs with focus/error states
- [ ] Data table styles
- [ ] Nav/sidebar styles
- [ ] Modal styles

**JavaScript (`static/js/app.js`)**
- [ ] HTMX configuration
- [ ] Nav scroll state: `window.scrollY > 40` toggles glassmorphism
- [ ] Notification polling: `hx-trigger="every 30s"` on bell icon
- [ ] Smooth scroll for anchor links with 80px nav offset
- [ ] Scroll reveal: IntersectionObserver (threshold 0.12, rootMargin -40px) adding `.visible` class
- [ ] Animated counters: `requestAnimationFrame` + ease-out cubic for stat cards
- [ ] `prefers-reduced-motion` check to disable animations

**Responsive CSS (`static/css/responsive.css`)**
- [ ] Tablet breakpoint (≤ 1024px): 2-column grids, hero visual hidden
- [ ] Mobile breakpoint (≤ 768px): 1-column grids, nav links hidden
- [ ] Small mobile breakpoint (≤ 480px): stat cards 2-column, buttons full-width

### 4.2 — Landing Page

**Template (`templates/landing/index.html`)**
- [ ] Extends `base.html`
- [ ] Hero section: company name, headline, subheadline, two CTAs, animated dashboard mock
- [ ] Module strip: Core, Attendance, HSE, Payroll with icon cards
- [ ] Stats band: 4 stat cards with animated counters (e.g. "1,200+ Employees Managed")
- [ ] Feature grid: 2-column cards for key differentiators
- [ ] Industry section: 4-column cards (Manufacturing, Construction, Mining, Office)
- [ ] How it works: 3-step process cards
- [ ] Compliance section: 2-column with regulatory badges (PPh 21, BPJS, ISO 45001)
- [ ] CTA band: "Get Started" with form or button
- [ ] Footer: 4-column layout (brand, product, company, legal)
- [ ] Floating decorative cards with float animation (removed at ≤ 1024px)

**Landing CSS (`static/css/landing.css`)**
- [ ] All landing-page-specific styles
- [ ] Section bands alternating `--color-bg` and `--color-bg-card-2`
- [ ] Section header anatomy: tag pill + h2 + description
- [ ] Scroll reveal classes: `.reveal`, `.reveal-delay-1` through `.reveal-delay-4`

### 4.3 — Authentication Templates

**Login (`templates/auth/login.html`)**
- [ ] Extends `base.html` (no sidebar/topbar)
- [ ] Centered card with email + password form
- [ ] "Forgot Password" link
- [ ] Error display for invalid credentials
- [ ] HTMX form submission to `/api/v1/auth/login`, stores tokens in localStorage

**Password Reset Request (`templates/auth/password-reset.html`)**
- [ ] Email input → sends reset email
- [ ] Success message: "If this email is registered, a reset link has been sent"

**Password Reset Confirm (`templates/auth/password-reset-confirm.html`)**
- [ ] New password + confirmation form
- [ ] Token from URL parameter
- [ ] Redirects to login on success

### 4.4 — Dashboard Layout

**Dashboard Base (`templates/dashboard/base.html`)**
- [ ] Extends `base.html`
- [ ] Full sidebar + topbar layout
- [ ] Role-aware dashboard landing at `/dashboard/`
- [ ] Sidebar items gated by role and subscription tier

**Dashboard CSS (`static/css/dashboard.css`)**
- [ ] Dashboard-specific styles: sidebar, topbar, content area layout
- [ ] Page header: title + breadcrumbs + action buttons
- [ ] Content grid for dashboard widgets

### 4.5 — Core Module Templates

**Employee List (`templates/core/employees/list.html`)**
- [ ] Paginated employee table with columns: emp_number, name, department, position, status, join_date
- [ ] Filter bar: department, status, position, employment_type, search by name/emp_number
- [ ] "Add Employee" button → opens modal or navigates to create page
- [ ] HTMX: filters and pagination update content area without full page reload
- [ ] Bulk import link

**Employee Detail (`templates/core/employees/detail.html`)**
- [ ] Tabs: Personal Info, Employment, Documents, Attendance History, Leave, Payroll
- [ ] Employee header: name, emp_number, department, position, status badge, action buttons (Edit, Deactivate)
- [ ] Each tab content loaded as HTMX partial on tab click

**Employee Create/Edit (`templates/core/employees/form.html`)**
- [ ] Form fields for all Employee model fields
- [ ] "Create Login Account" toggle
- [ ] Validation errors inline below each field
- [ ] HTMX form submission with error handling

**Employee Documents (`templates/core/employees/documents.html`)**
- [ ] Document list: type badge, filename, valid_until, verified status
- [ ] Upload button → opens upload modal
- [ ] Download button → requests signed URL and redirects

**Department List (`templates/core/departments/list.html`)**
- [ ] Tree view of departments (parent → child)
- [ ] Add/Edit/Deactivate actions

**Position List (`templates/core/positions/list.html`)**
- [ ] Table of positions with department, level, salary range
- [ ] Add/Edit/Deactivate actions

### 4.6 — Attendance Module Templates

**Attendance Log List (`templates/attendance/logs/list.html`)**
- [ ] Paginated log table: employee, date, clock_in, clock_out, status, overtime
- [ ] Filters: employee, department, date range, status
- [ ] "Submit Correction" action on each row

**Shift List (`templates/attendance/shifts/list.html`)**
- [ ] Shift table with name, start/end times
- [ ] "Assign Employees" action → opens shift assignment modal

**Leave Request List (`templates/attendance/leave/requests/list.html`)**
- [ ] Table: employee, leave type, dates, reason, status, action
- [ ] Filter by status (pending/approved/rejected)
- [ ] Approve/Reject actions with reason input

**Leave Type List (`templates/attendance/leave/types/list.html`)**
- [ ] Leave types table with name, default days, carry-over flag
- [ ] Add/Edit/Deactivate actions

### 4.7 — HSE Module Templates

**HSE Dashboard (`templates/hse/dashboard.html`)**
- [ ] Summary widgets: open violations, expiring inductions, active permits
- [ ] Charts: violations by severity, man-hours by department

**Violation List (`templates/hse/violations/list.html`)**
- [ ] Table: employee, severity badge, status badge, incident date, description preview
- [ ] Filter by severity, status, date range
- [ ] "Report Violation" button

**Man-Hours (`templates/hse/man-hours/list.html`)**
- [ ] Summary table by department/period
- [ ] Export to CSV/PDF button

**Induction List (`templates/hse/inductions/list.html`)**
- [ ] Table: employee, type, valid_until, status (valid/expiring/expired)
- [ ] Expiring-soon filter (14 days)
- [ ] "Record Induction" button

**Work Permit List (`templates/hse/work-permits/list.html`)**
- [ ] Table: type badge, status badge, location, dates, requester
- [ ] Filter by status, type, date
- [ ] "Create Work Permit" button

### 4.8 — Payroll Module Templates

**Payroll Run List (`templates/payroll/runs/list.html`)**
- [ ] Table: period, status badge, initiated date, initiated by, employee count
- [ ] "Initiate Payroll Run" button → opens modal with year/month selection

**Payroll Run Detail (`templates/payroll/runs/detail.html`)**
- [ ] Run summary: period, status, dates, initiated by
- [ ] Payslip table: employee, gross, deductions, net, status
- [ ] "Finalize" button (if draft) or "View Only" (if finalized)
- [ ] "Download Summary" button

**Payslip Detail (`templates/payroll/payslips/detail.html`)**
- [ ] Employee info header
- [ ] Breakdown: base salary, allowances, overtime, gross
- [ ] Deductions: BPJS TK employee/company, BPJS KES employee/company, PPh 21
- [ ] Net salary (highlighted)
- [ ] "Download PDF" button → signed URL
- [ ] "Mark Disbursed" button (if finalized, not yet disbursed)

### 4.9 — HTMX Partial Templates

Create partial templates for each dynamic section (no full page shell, just content):

```
templates/partials/
├── employees/
│   ├── _list_row.html
│   ├── _form.html
│   └── _detail_tabs.html
├── attendance/
│   ├── _log_row.html
│   └── _leave_request_row.html
├── hse/
│   └── _violation_row.html
└── payroll/
    └── _payslip_row.html
```

Each partial receives the minimum data needed and renders within the existing page context.

### 4.10 — Settings & Profile Templates

**Company Settings (`templates/settings/company.html`)**
- [ ] Company profile form: name, industry, address, geofence coordinates
- [ ] Save via HTMX

**Subscription Settings (`templates/settings/subscription.html`)**
- [ ] View current plan and enabled modules
- [ ] Contact sales / upgrade prompt (read-only in v1)

**User Management (`templates/settings/users.html`)**
- [ ] User list with role badges
- [ ] Invite user form (email + role)

---

## Definition of Done — Implementation Complete

- [ ] All four tracks (Configuration, Modules, API, Templates) implemented in order
- [ ] Every model has corresponding selectors, services, serializers, views, and templates
- [ ] Tenant isolation verified: cross-company access returns 403
- [ ] All API endpoints match OpenAPI schemas
- [ ] All write endpoints have negative-path tests
- [ ] Coverage targets met: core 85%, attendance 80%, hse 80%, payroll 85%, shared 90%
- [ ] Formatter/linter runs clean on all modified files
- [ ] All forms submit via HTMX with proper error handling
- [ ] All pages render correctly with design tokens applied
- [ ] Mobile-responsive breakpoints tested
- [ ] `prefers-reduced-motion` respected
