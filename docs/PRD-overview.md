# PRD — Nexus HR: Centralized Employee Data Management System

**Version**: 1.2 | **Date**: July 4, 2026 | **Status**: Active Development

---

## Executive Summary

Nexus is a **SaaS Centralized Employee Data Management System** designed for manufacturing, construction, mining, and general office industries. The platform positions **Employee data as the central core entity**, feeding all operational modules.

**Four core modules**:

| Module | Purpose |
|--------|---------|
| **Core** | Employee master data, departments, positions, documents, user authentication |
| **Attendance & Leave** | Mobile clock-in/out (GPS + photo), shift management, leave requests and approvals |
| **HSE + Man Hours** | Violations, man-hours aggregation, induction management, work permits, license tracking |
| **Payroll** | Payroll calculation, Payslip generation, overtime, PPh 21, BPJS deductions |

**Clock-in/clock-out is mobile-only for all users** — employees, managers, and HR admins all use the Flutter app. The **web dashboard is for administrative work**: Employee CRUD, payroll processing, HSE oversight, and approvals.

Companies pay a **subscription per active employee per month** with additive module tiers.

---

## Key Differentiators

- **Industry-Specific Design**: Pre-configured policies for manufacturing shifts, construction safety, mining remote ops, office flexibility
- **Offline-First Mobile**: Clock in/out without internet; auto-sync when online
- **Fraud-Resistant Attendance**: GPS geofencing, photo verification, shift validation, induction expiry checks
- **Comprehensive HSE Management**: Man-hours tracking, safety violations with photo evidence, multi-step work permits, induction/license validity
- **Indonesian Payroll Compliance**: PPh 21 (UU HPP No. 7/2021), BPJS Ketenagakerjaan/Kesehatan, configurable PTKP
- **True Multi-Tenancy**: Complete data isolation per company with tenant-scoped queries at every layer

---

## Product Vision

### Mission Statement

To empower companies across manufacturing, construction, mining, and office sectors with a unified HR platform that combines operational efficiency, safety compliance, and employee self-service — reducing administrative overhead while increasing workforce visibility and regulatory adherence.

### Core Principles

1. **Employee-Centric Data Model**: Every module references the Employee entity — single source of truth
2. **Mobile Accessibility**: Frontline workers interact via mobile; managers and HR via web dashboard
3. **Fraud Prevention**: Location verification, offline detection, approval workflows, and immutable audit trails
4. **Industry Adaptation**: Default policies per industry (manufacturing shifts vs. project-based construction vs. general office hours)
5. **Regulatory Compliance**: Indonesian labor law (Manaker), PPh 21 (UU HPP), BPJS, ISO 45001, OSHA

---

## Target Market

### Primary Industries

| Industry | Characteristics | Primary Use Cases |
|----------|----------------|-------------------|
| **Manufacturing** | Fixed facilities, shift work, production floor safety | Shift scheduling, geofenced clock-in, machine safety permits, man-hours |
| **Construction / Contractor** | Multi-site projects, mobile workforce, high safety risk | Project-based attendance, work permits (hot work, confined space), violations |
| **Mining** | Remote locations, extreme safety, offline needs | Remote clock-in with offline sync, critical HSE compliance, isolation permits |
| **General Office** | Flexible schedules, WFH-capable, lower safety priority | Standard attendance, leave management, performance reviews |

### Company Size

- **Small (10–50 employees)**: Core + Attendance tier
- **Medium (50–500 employees)**: Core + Attendance + HSE tier
- **Large (500+ employees)**: Full Suite with Payroll + Performance + Documents

### Geography

- **Phase 1**: Indonesia (Bahasa Indonesia UI, PPh 21 payroll, BPJS integration)
- **Future**: Southeast Asia (Malaysia, Philippines, Thailand) and beyond

---

## User Personas

### 1. Platform Admin (SaaS Operator)

**Credentials**: `AuthUser.is_superuser = True`, `is_staff = True` — no `Employee` record, no company scope
**Access**: Django admin (`/admin/`) only — full read/write across all tenants
**Goals**: Manage tenant registrations, subscription tiers, platform health, cross-company metrics
**Key rules**:
- Not associated with any company — bypasses all `company_id` filters
- Created manually via `manage.py createsuperuser` (never through self-registration)
- Never issued a JWT for the HR dashboard

### 2. HR Administrator

**Access**: Web dashboard — full read/write across all modules within their company
**Goals**:
- Maintain accurate employee master data
- Configure company policies (attendance rules, leave types, shift schedules)
- Approve/reject leave requests and attendance disputes
- Generate & processing payroll for all employees
- Monitor safety compliance (violations, inductions, man-hours)
- Export reports for audits and management

**Pain Points** (solved by Nexus): Scattered data across Excel/paper, manual payroll errors, no real-time attendance visibility, difficulty enforcing geofencing.

### 3. Manager / Supervisor

**Access**: Web dashboard — read access to own team, approval permissions for leave/attendance
**Goals**:
- View team attendance in real-time
- Approve or reject leave requests
- Monitor team safety compliance (inductions, violations)
- Review overtime and shift adherence

**Pain Points** (solved by Nexus): No real-time presence visibility, leave requests via WhatsApp, no alerts for expired inductions.

### 4. Employee (Frontline Worker)

**Access**: Mobile app (Flutter) — self-service only
**Goals**:
- Clock in/out quickly with GPS verification
- Submit leave requests, view own attendance history and leave balances
- Access digital payslips
- Report safety violations or near-misses

**Pain Points** (solved by Nexus): Manual sign-in sheets, no leave balance visibility, lost paper payslips, no easy safety reporting.

### 5. HSE Officer (Safety Compliance)

**Access**: Web dashboard — full HSE module access
**Goals**:
- Track man-hours for ISO 45001 / OSHA reporting
- Monitor open work permits (Hot Work, Confined Space, LOTO)
- Review and resolve safety violations
- Ensure employees have valid inductions before site access

**Pain Points** (solved by Nexus): Manual spreadsheet man-hours tracking, paper work permits, no automatic induction expiry alerts, difficult audit metric aggregation.

---

## Feature Requirements by Module

### Core Module

- Employee master data CRUD with auto-generated `emp_number` (NXS-0001 format)
- Department management with hierarchical org-chart (parent → child)
- Position management with salary bands (min/max)
- Employee status lifecycle: active → inactive → resigned → terminated
- Employee document storage (KTP, NPWP, contracts, certificates) with S3 + signed URLs
- Custom authentication with email login (no username)
- JWT access/refresh tokens with revocation
- Role-based access: platform_admin, hr_admin, manager, employee, hse_officer
- Audit logging for all write operations
- Multi-tenant data isolation per company
- Subscription plan management (module feature flags)

### Attendance & Leave Module

- Mobile clock-in with GPS geofencing validation (configurable radius)
- Mobile clock-out with photo verification
- Offline-first clock-in with auto-sync (72h backdate window)
- Shift management (create, assign, schedule)
- Leave type configuration (annual, sick, maternity, etc.)
- Leave request submission → manager approval/rejection workflow
- Leave balance tracking with carry-over rules
- Attendance status: present, absent, late, half_day
- Attendance correction by HR Admin
- Leave balance deduction on approval
- Year-boundary leave handling

### HSE + Man Hours Module

- Safety violation reporting with photo evidence and severity levels (low, medium, high, critical)
- Violation lifecycle: open → in_review → resolved
- Man-hours aggregation from attendance logs (Celery background tasks)
- Man-hours summary by department and period
- Induction management with expiry tracking and alerts (14 days before)
- Work permit system: hot_work, confined_space, loto, working_at_height
- Work permit lifecycle: draft → pending_approval → approved → active → closed → expired
- License tracking with expiry alerts (30 days before)
- ISO 45001 / OSHA reporting support

### Payroll Module

- Payroll run initiation per period (year + month)
- Payslip generation for all active employees
- Base salary + allowances + overtime calculation
- BPJS Ketenagakerjaan calculation (employee 2%, company 3.7%)
- BPJS Kesehatan calculation (employee 1%, company 4%, capped at Rp 12,000,000)
- PPh 21 calculation per UU HPP No. 7/2021 (gross-up for permanent, nett for contract)
- PTKP configuration: TK0–TK3, K0–K3
- Payroll run finalization (lock, no further edits)
- Payslip PDF download via signed URL
- Disbursement recording (bank transfer reference)
- Idempotency protection on payroll runs

---

## Non-Functional Requirements

- **Multi-tenancy**: Complete data isolation per company at every query layer
- **Security**: JWT Bearer auth, refresh token revocation, hashed token storage, PII masking in logs
- **Rate limiting**: 10 req/min auth, 300 req/min reads, 60 req/min writes, 20 req/min uploads
- **Pagination**: Default 25, max 100 per page — no unbounded responses
- **Idempotency**: Required on critical POST endpoints (employee create, payroll run, disburse)
- **Error handling**: Standardized error envelope across all endpoints
- **Logging**: Structured JSON logging via structlog — no PII in logs
- **File storage**: S3-compatible with private ACL and signed URLs (15-min expiry)
- **Cross-tenant security**: 403 (not 404) for cross-company resource access
- **Offline sync**: Mobile records accepted within 72h backdate window
- **Testing**: 80–90% line coverage per module
- **Background tasks**: Celery + Redis for async payroll, man-hours aggregation, expiry alerts
