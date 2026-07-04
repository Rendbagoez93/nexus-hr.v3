# User Journey Flow — Nexus HR

**Version**: 1.2 | **Date**: July 2026 | **Status**: **Status**: Derived from PRD + API Design + Gaps from v.1.0

---

## 1. Web Dashboard Navigation & Information Architecture 

Closes gap: *Web Dashboard Navigation Structure*.

### 1.1 Layout

The web dashboard is server-rendered Django templates with HTMX — no client
router, no SPA state. The shell is persistent across navigation:

- **Topbar**: company name/logo, current user + role badge, notification
  bell (see §7.5), user menu (Profile, Log Out).
- **Sidebar**: role- and subscription-filtered navigation (below).
- **Main content area**: swapped via `hx-boost` on sidebar/in-page links —
  the server returns a full page on direct load and a content-only partial
  on HTMX navigation, so both work without duplicating templates.
- **Breadcrumb**: derived from the URL path, shown under the topbar, since
  there's no client-side route history to lean on for orientation.

### 1.2 Sidebar structure

Every item below is additionally gated by `company.subscription.has_module(...)`
— a company without the HSE add-on never sees the HSE section rendered,
regardless of role.

| Section | Items | Visible to |
|---|---|---|
| Core | Dashboard, Employees, Departments, Positions, Sites & Projects | HR Admin |
| Attendance & Leave | Attendance, Shifts, Leave Requests, Leave Types | HR Admin, Manager (scoped) |
| HSE + Man Hours | HSE Dashboard, Violations, Man-Hours, Inductions, Work Permits | HR Admin, HSE Officer, Manager (read-only) |
| Payroll | Payroll Runs, Payroll Settings | HR Admin only |
| Cross-cutting | Reports, Settings (Company, Subscription, Users) | HR Admin (full); Manager/HSE Officer see only the Reports tab scoped to their data |

Manager and HSE Officer never see Employees CRUD, Payroll, or Settings —
those are HR Admin-only regardless of subscription tier.

### 1.3 URL convention

```
/dashboard/                                  → role-aware landing dashboard
/dashboard/employees/                        → list
/dashboard/employees/<emp_number>/           → detail (tabbed)
/dashboard/employees/<emp_number>/edit/      → edit form
/dashboard/departments/ , /positions/        → same list/detail/edit pattern
/dashboard/sites/                            → Sites & Projects (§3.11)
/dashboard/attendance/                       → oversight list
/dashboard/shifts/                           → list + assignment (§3.7)
/dashboard/leave/requests/ , /leave/types/
/dashboard/hse/violations/ , /man-hours/ , /inductions/ , /work-permits/
/dashboard/payroll/runs/ , /payroll/runs/<id>/
/dashboard/reports/                          → §7.6
/dashboard/settings/company/ , /subscription/ , /users/
```

One namespace per module keeps the `TenantMiddleware` + role-permission
decorator applicable uniformly per prefix instead of per view.

---

## 2. Platform Admin Journeys (Django Admin `/admin/`)

### 2.1 Tenant Onboarding

Platform Admin logs into Django Admin
→ Navigates to Companies
→ Clicks "Add Company"
→ Fills: name, industry, subscription tier
→ Saves
→ Company created (clean slate: no users, no employees)
→ Navigates to Subscription Plans
→ Assigns plan to company
→ Modules unlocked based on plan (attendance, hse, payroll flags)

### 2.2 Platform Health Monitoring

Platform Admin logs into Django Admin
→ Views cross-company metrics
→ Reviews AuditLog entries
→ Manages subscription tiers

---

## 3. HR Administrator Journeys (Web Dashboard)

### 3.1 Registration & Onboarding Wizard

#### 3.1.1 Registration

HR Admin opens web dashboard → sees login screen → clicks "Register Account"
→ Fills: email, password (with confirmation)
→ Clicks "Register Account"
→ Backend validates registration data
→ ✅ Valid: Company + AuthUser created (unverified), confirmation email sent
→ HR Admin checks email → clicks confirmation link → account verified
→ HR Admin logs in (§3.2) → redirected into the Onboarding Wizard (§3.1.2)
→ ❌ Invalid (duplicate email, weak password, etc.): validation error shown
on the registration form

*(No Platform Admin invitation is required — HR Admin can self-register.
The confirmation email prevents spam accounts; the Onboarding Wizard that
follows ensures the company is properly configured before any operational
data exists.)*

#### 3.1.2 Onboarding Wizard

First login after registration → redirected into a setup wizard instead of
the bare dashboard
→ Wizard is skippable at every step (banner persists on the dashboard
listing remaining steps until the company is fully configured)

**Step 1 — Company Profile**: confirm industry, add company address and
site coordinates + default geofence radius (used by §5.2 Clock-In), upload
logo.
→ **Step 2 — Departments**: create at least one, or accept an
auto-created "General" department to unblock later steps.
→ **Step 3 — Positions**: create at least one, or accept a small set of
sensible defaults (Staff, Supervisor, Manager).
→ **Step 4 — Shifts**: define at least one default shift (e.g. "Day Shift,
08:00–17:00") — required before any employee can be assigned a shift.
→ **Step 5 — Leave Types** *(if Attendance & Leave module enabled)*:
accept Nexus defaults (Annual, Sick, Maternity) or customize days/carry-over.
→ **Step 6 — HSE Setup** *(if HSE module enabled)*: define induction types
relevant to the company's industry.
→ **Step 7 — Payroll Setup** *(if Payroll module enabled)*: company BPJS
registration numbers, payroll cycle date, default PPh 21 TER category
mapping reference.
→ **Step 8 — Employees**: add the first employees individually or via
Bulk Import (§3.5), or skip and do this later.
→ Completion screen → lands on the normal dashboard; a "Setup checklist"
widget remains visible until every non-skippable step is done.

### 3.2 Authentication Flow

HR Admin opens web dashboard
→ Sees login screen
→ Enters email + password
→ System validates credentials
→ ✅ Valid: Returns access_token + refresh_token
→ Dashboard loads with company-scoped data
→ ❌ Invalid: Returns 401 "Invalid credentials"
→ Login screen shows error message

*(Forgot-password link on this screen leads to §7.4.)*

### 3.3 Department Management

HR Admin navigates to Departments section
→ Sees org-chart tree of all company departments
→ Clicks "Add Department"
→ Fills: name, code, parent department (optional)
→ Submits
→ ✅ Created: Department appears in tree
→ ❌ Duplicate code: Error shown
→ Clicks existing department
→ Views department details + child departments
→ Clicks "Edit"
→ Modifies name/code/parent
→ Saves → Updated
→ Clicks "Deactivate"
→ Confirm dialog → Soft-deleted (is_active=False)
→ Historical records retain reference

### 3.4 Position Management

HR Admin navigates to Positions section
→ Sees list of positions (filterable by department)
→ Clicks "Add Position"
→ Fills: title, level (staff/supervisor/manager/senior_manager/director),
department, base_salary_min, base_salary_max
→ Submits
→ ✅ Created: Position appears in list
→ ❌ min > max salary: Validation error
→ Clicks existing position → Edit/Deactivate

### 3.5 Employee Management

#### Create Employee

HR Admin navigates to Employees section
→ Sees paginated employee list (filterable by department, status, position, employment_type)
→ Clicks "Add Employee"
→ Fills: full_name, email, department, position, employment_type,
join_date, tax_status, NPWP, BPJS numbers, bank details
→ Toggles "Create Login Account" (yes/no)
→ Yes: System creates AuthUser + Employee in one transaction
→ No: Employee only (no login capability)
→ Submits
→ ✅ Created: emp_number auto-generated (NXS-0001), employee appears in list
→ ❌ Duplicate email in company: Error

#### View / Edit Employee

HR Admin clicks employee in list
→ Employee detail page loads
→ Tabs/sections: Personal Info, Employment, Documents, Sites & Projects, Attendance History, Leave, Payroll
→ Clicks "Edit" → Modifies fields → Saves
→ Clicks "Deactivate"
→ Fills: status (resigned/terminated), resign_date, reason
→ Confirms → Employee status updated

#### Upload Employee Document

HR Admin navigates to employee's Documents tab
→ Clicks "Upload Document"
→ Selects doc_type (ktp, npwp, contract, ijazah, sim, sertifikat, other)
→ Uploads file → File stored in S3 (private ACL)
→ Sets valid_until date (optional)
→ Submits
→ ✅ Document created → Signed URL generated on retrieval (15-min expiry)

#### Bulk Employee Import

HR Admin navigates to Employees → clicks "Bulk Import"
→ Uploads a CSV file containing employee data (no system-provided template
— HR Admin uses their own CSV)
→ System matches uploaded CSV column names against database columns:
→ ✅ Column name matches a database field: data mapped automatically
(including `emp_number` — if the CSV provides one, it overrides the
system-generated value)
→ ❌ Column name does not match any database field: flagged as a conflict
→ **Preview screen**: shows matched columns and any column-name conflicts;
for each conflict, HR Admin can either:
- **Rename** the CSV column to map it to the correct database field via the
  UI, or
- **Exclude** that column from the import (its data is skipped)
→ Once all column conflicts are resolved and data is valid, HR Admin
confirms import → processed as a Celery task (large files shouldn't block
the request) → creates Employee (+ AuthUser where `create_login=yes`) per
valid row
→ HR Admin notified when the task completes: X created, with a downloadable
error report CSV for any rows that failed data-level validation
(skipped rows)

### 3.6 Attendance Oversight

HR Admin navigates to Attendance section
→ Sees attendance logs (paginated, filterable by employee, department, date range, status)
→ Clicks a log entry → Views clock-in/out details, GPS, photo
→ Clicks "Submit Correction"
→ Modifies attendance record → Saves

#### Reviewing Disputed Attendance Records

Closes part of gap: *Attendance Dispute Flow* (employee-initiated side is §5.4).

HR Admin filters Attendance list by status = "Disputed"
→ Clicks a disputed record → sees employee's stated reason + any evidence
photo alongside the original clock-in/out data
→ Clicks "Approve Dispute" → applies the correction the employee requested
(reuses the same correction mechanic as the section above, with the dispute
linked as the reason) → employee notified (§7.5)
→ Clicks "Reject Dispute" → fills a reason → record stands unchanged →
employee notified with the reason
→ Either action writes an AuditLog entry referencing the dispute

This differs from an HR-initiated correction above it: a dispute always
requires an explicit HR decision before anything changes, since the request
originated from the employee, not from HR noticing an error itself.

### 3.7 Shift Management

HR Admin navigates to Shifts section
→ Sees list of shifts
→ Clicks "Add Shift"
→ Defines shift name, start/end times, break rules
→ Saves
→ Edits/Deactivates existing shifts

#### Assigning Shifts to Employees 

HR Admin opens a shift → "Assign Employees" tab
→ Two assignment paths:
- **Individual**: search an employee → assign this shift with an
  `effective_from` date (and optional `effective_until`, blank = ongoing).
- **Bulk**: filter employees by department/position → select matching
  employees → assign the same shift with the same effective date range to
  all of them in one action.
→ ✅ Assigned: if the employee had a different active shift overlapping the
new effective range, that prior assignment's `effective_until` is
automatically closed off the day before the new one starts (no overlapping
active assignments for one employee)
→ The employee's currently-active `ShiftAssignment` is what the mobile app
uses to show "today's shift" and what attendance logic uses for
late/early-clock-in calculations

*(Rotating shift patterns, e.g. 4-on/3-off, aren't modeled here — flag if
the business needs them; the current model assumes one effective shift at a
time per employee.)*

### 3.8 Leave Management

#### Configure Leave Types

HR Admin navigates to Leave Types
→ Creates leave types (annual, sick, maternity, etc.)
→ Sets: name, default_days, carry_over_allowed

#### Process Leave Requests

HR Admin navigates to Leave Requests
→ Sees all pending/approved/rejected requests
→ Clicks pending request
→ Reviews: employee, dates, reason, leave balance
→ Clicks "Approve" → Status → approved, balance deducted
→ Clicks "Reject" → Fills reason → Status → rejected

### 3.9 Payroll Processing

HR Admin navigates to Payroll section
→ Clicks "Initiate Payroll Run"
→ Selects: period_year, period_month
→ Adds Idempotency-Key header
→ Submits
→ ✅ Payroll run created (status: draft)
→ Celery task calculates payslips for all active employees:
base_salary + allowances + overtime - BPJS_TK - BPJS_KES - PPh21
→ ❌ Duplicate run for same period: 409 Conflict
→ Reviews payroll run detail
→ Views all generated payslips
→ Clicks "Finalize" → Run locked (no further edits)
→ Views individual payslip
→ Clicks "Download PDF" → Signed URL generated
→ Clicks "Mark Disbursed" → Records bank transfer reference

### 3.10 HSE Oversight

HR Admin navigates to HSE section
→ Views dashboard: open violations, expiring inductions, active work permits
→ Reviews safety violations (filterable by severity, status, date)
→ Monitors man-hours summary by department/period

### 3.11 Multi-Site / Project Assignment 

A company can register multiple **Sites** (name, address, GPS coordinates +
geofence radius, site type — office/factory/mine/construction-project).
Every employee has a **primary Site** (their geofencing default), and for
construction/mining work can additionally have time-bound **Project**
assignments tied to a Site.

HR Admin navigates to Sites & Projects
→ Clicks "Add Site" → fills name, address, coordinates, geofence radius,
site type → saves
→ Clicks "Add Project" → fills project name, linked Site, start/end dates
→ saves
→ From an employee's detail page → "Sites & Projects" tab → "Assign to
Project" → selects project, role on project, start/end dates
→ ✅ Assigned: while a `ProjectAssignment` is active, it takes priority over
the employee's primary Site for: (a) which geofence is checked at clock-in
(§5.2), (b) which project man-hours are aggregated against (§6.2), and (c)
which site-specific induction requirements apply (§6.3)
→ When the assignment's end date passes, the employee reverts to their
primary Site automatically
→ In case the projects is still ongoing, while assignment's end date is approaching, HR Admin will get a notification for the project is ending and can extend the end date accrodingly as long as the project is still ongoing. 

---

## 4. Manager / Supervisor Journeys (Web Dashboard)

### 4.1 Team Attendance View

Manager logs in → Dashboard
→ Sees team attendance in real-time
→ Who is clocked in, who is absent, who is on leave
→ Filterable by department

### 4.2 Leave Approval

Manager navigates to Leave Requests
→ Sees pending requests from own team
→ Clicks request
→ Reviews: employee, dates, reason
→ Clicks "Approve" → Status → approved
→ Clicks "Reject" → Fills reason → Status → rejected

### 4.3 Team Safety Compliance

Manager views team safety status
→ Sees induction status, violations for team members
→ Alerts for expiring inductions

### 4.4 Work Permit Approval

Manager navigates to Work Permits → filters by status "pending_approval"
→ Sees permits submitted by Employees (after HSE Officer pre-approval) and
permits submitted directly by HSE Officers
→ Clicks a pending permit → reviews: permit type, description, location,
start/end dates, safety checklist, and (for employee-submitted permits)
the HSE Officer's prior review notes
→ Clicks "Approve" → Status: approved → active
→ Submitter notified (§7.5): Employee or HSE Officer receives confirmation
→ Clicks "Reject" → fills reason → Status: rejected
→ Submitter notified with the rejection reason

---

## 5. Employee Journeys (Mobile App — Flutter)

### 5.1 First-Time App Onboarding

Employee downloads the app → opens for the first time → Welcome screen →
"Log In" (no public sign-up — accounts are created by HR Admin only, per
§3.5)
→ Enters company-issued email + password (if the account was just created,
this is the temporary/invite password and the app prompts a forced password
change before continuing, reusing the §7.4 reset mechanics)
→ ✅ Login succeeds → app requests **Location permission** ("needed to
verify you're at your work site when you clock in") and **Camera
permission** ("needed for your clock-in photo") — both required
→ ❌ Either permission denied → blocking screen explaining clock-in won't
work until granted, with a button that opens device settings directly
→ Notification permission requested separately and is skippable
→ Lands on Home screen (§5.2) showing the Employee's name, Department, and Position, 
clock-in button, today's date, today's shift, and leave balance summary. 
→ **Edge case**: employee has no Site/Project assignment yet → Home screen
shows "No work site assigned — contact HR" instead of a geofence-based
clock-in button

### 5.2 Clock-In Flow

Employee opens app
→ Sees home screen with clock-in button
→ Taps "Clock In"
→ App captures GPS coordinates
→ ✅ Within geofence radius:
→ App prompts for photo
→ Employee takes photo
→ Submits clock-in record
→ ✅ Online: Record sent to server immediately
→ ❌ Offline: Record stored locally, auto-synced when online
→ Server validates clocked_at within 72h window
→ ❌ Outside geofence:
→ Error shown: "You are outside the allowed work area"
→ [GAP: Is there an override request flow?]

### 5.3 Clock-Out Flow

Employee taps "Clock Out"
→ App checks for time
→ App captures GPS + photo
→ Submits clock-out record
→ Server pairs with most recent clock-in and overtime form
→ Calculates work hours, overtime

### 5.4 Disputing an Attendance Record 

Employee navigates to Attendance History
→ Taps a record they believe is wrong (e.g. a missed clock-out, a system
error)
→ Taps "Dispute This Record"
→ Fills a reason, optionally attaches an evidence photo
→ Submits
→ ✅ Dispute created (status: pending) → visible to HR Admin under
Attendance, filterable by "Disputed" (§3.6)
→ Employee sees the dispute's status (pending/approved/rejected) under
Attendance History and is notified (§7.5) once HR Admin acts on it

### 5.5 Leave Request

Employee navigates to Leave section
→ Sees leave balances (annual, sick, etc.)
→ Taps "Request Leave"
→ Selects leave type
→ Selects start date, end date
→ Fills reason
→ Submits
→ ✅ Request created (status: pending)
→ Waits for manager approval
→ Views request history
→ Sees status: pending / approved / rejected
→ Can edit/cancel while still pending

### 5.6 View Payslip

Employee navigates to Payslips section
→ Sees list of payslips by period
→ Taps a payslip
→ Views: base salary, allowances, deductions, net salary
→ Taps "Download PDF" → Signed URL → PDF downloaded

### 5.7 Report Safety Violation

Employee navigates to Safety section
→ Taps "Report Violation"
→ Fills: description, severity, photo evidence
→ Submits
→ Violation record created

### 5.8 Submit Work Permit

Employee navigates to Safety → "Work Permits" → taps "Submit Work Permit"
→ Selects: permit_type (hot_work, confined_space, loto, working_at_height)
→ Fills: description, location, start/end dates, safety checklist
→ Submits → Status: draft → pending_approval
→ **Stage 1 — HSE Officer review**: Employee notified once HSE Officer acts
→ ✅ HSE Officer approves → forwarded to Manager for final approval
→ ❌ HSE Officer rejects → Employee notified with rejection reason → Status: rejected
→ **Stage 2 — Manager approval**: Employee notified once Manager acts
→ ✅ Manager approves → Status: approved → active → Employee notified
→ ❌ Manager rejects → Employee notified with rejection reason → Status: rejected
→ Employee can view current status (pending/approved/rejected) under
Safety → Work Permits

### 5.9 View Own Profile

Employee navigates to Profile
→ Views: personal info, department, position, employment status, employment detail, salary amount
→ Read-only (changes must go through HR Admin)

---

## 6. HSE Officer Journeys (Web Dashboard)

### 6.1 Safety Violation Management

HSE Officer navigates to Violations
→ Sees list of violations (filterable by severity, status, date range, employee)
→ Clicks "Report Violation"
→ Fills: employee, severity (low/medium/high/critical), description, photo evidence
→ Submits → Violation created (status: open)
→ Clicks existing violation
→ Reviews details
→ Updates status: open → in_review → resolved

### 6.2 Man-Hours Reporting

HSE Officer navigates to Man-Hours
→ Views aggregated man-hours (by department, period, and — where
Project assignments exist, §3.11 — by project)
→ Exports for ISO 45001 / OSHA reporting (uses the general export mechanic
in §7.6)
→ Data derived from attendance logs by Celery background tasks

### 6.3 Induction Management

HSE Officer navigates to Inductions
→ Sees all induction records
→ Filters: expired, expiring within N days
→ Clicks "Record Induction"
→ Selects employee, induction type, valid_until date
→ Submits
→ Marks induction as verified
→ System alerts 14 days before expiry

### 6.4 Work Permit Management

Work permits can be submitted by either an **Employee** or an **HSE Officer**.
The approval chain and post-approval actions differ by submitter.

#### Submitted by Employee

Employee navigates to Safety → "Work Permits" → taps "Submit Work Permit"
→ Selects: permit_type (hot_work, confined_space, loto, working_at_height)
→ Fills: description, location, start/end dates, safety checklist
→ Submits → Status: draft → pending_approval
→ **Approval step 1 — HSE Officer**: reviews permit →
→ ✅ Approves → forwarded to Manager for final approval
→ ❌ Rejects → fills reason → Status: rejected → Employee notified
→ **Approval step 2 — Manager (HSE)**: reviews permit →
→ ✅ Approves → Status: approved → active → Employee notified
→ ❌ Rejects → fills reason → Status: rejected → Employee notified
→ HSE Officer closes permit when work is complete → Status: closed
→ Permits auto-expire after valid_until → Status: expired

#### Submitted by HSE Officer

HSE Officer navigates to Work Permits
→ Sees permits (filterable by type, status, date)
→ Clicks "Create Work Permit"
→ Selects: permit_type (hot_work, confined_space, loto, working_at_height)
→ Fills: description, location, start/end dates, safety checklist
→ Submits → Status: draft → pending_approval
→ **Approval step — Manager (HSE)**: reviews permit →
→ ✅ Approves → Status: approved → active
→ ❌ Rejects → fills reason → Status: rejected
→ Once approved, HSE Officer can **assign the work permit** to an Employee
(binds the active permit to a specific employee for tracking purposes)
→ HSE Officer closes permit when work is complete → Status: closed
→ Permits auto-expire after valid_until → Status: expired

---

## 7. Cross-Cutting Flows

### 7.1 Token Refresh

Access token expires (after 60 min)
→ Client sends refresh token to /auth/token/refresh
→ ✅ Valid: New access_token returned
→ ❌ Expired/revoked: 401 → User redirected to login

### 7.2 Offline Sync (Mobile)

Employee clocks in while offline
→ Record stored locally with clocked_at timestamp
→ When online:
→ App syncs pending records
→ Server validates clocked_at within 72h of server time
→ ✅ Within window: Record accepted (is_offline_sync=True)
→ ❌ Beyond window: Record rejected

### 7.3 Cross-Tenant Isolation

Company A user sends request for Company B resource
→ TenantMiddleware scoping
→ Query returns no results (resource not in Company A scope)
→ Returns 403 Forbidden (never 404 — don't confirm existence)

### 7.4 Password Reset Flow 

User (any role, web or mobile) taps/clicks "Forgot Password" on the login
screen
→ Enters email
→ System always responds with the same message regardless of whether the
email exists ("If this email is registered, a reset link has been sent") —
deliberately avoids confirming which emails have accounts, consistent with
the no-404-on-cross-tenant principle in §7.3
→ ✅ If the email exists: a time-limited (1-hour), single-use reset token
is emailed
→ **Web**: link opens a reset-password page → enters new password twice →
submits → password updated → redirected to login
→ **Mobile**: the same link deep-links into the app's reset screen if
installed, otherwise opens a mobile web fallback page → same flow
→ On successful reset: the token is invalidated, and **all existing
refresh tokens for that user are revoked** — every device is forced to log
in again, since a password reset is a reasonable moment to assume the old
credential may have been compromised

### 7.5 Notification Flow 

**Trigger → recipient** pairs in this system:

| Event | Notified |
|---|---|
| HR Admin registration — email verification required | Registering HR Admin (verification email) |
| New employee account created | The new employee (welcome + set-password email) |
| Leave request submitted | Approving manager |
| Leave request approved/rejected | Requesting employee |
| Attendance dispute submitted | HR Admin |
| Attendance dispute resolved | Disputing employee |
| Payroll run finalized | Every employee with a payslip in that run |
| Induction/license/work permit expiring within N days | HSE Officer + affected employee |
| Bulk employee import completed | HR Admin (X created, downloadable error report if any rows failed) |
| Project assignment end date approaching | HR Admin (prompt to extend if project ongoing) |
| Work permit submitted by Employee | HSE Officer (pending Stage 1 review) |
| Work permit approved by HSE Officer (Stage 1) | Manager (pending final approval) |
| Work permit rejected by HSE Officer (Stage 1) | Submitting employee (with rejection reason) |
| Work permit approved by Manager (final) | Submitting employee or HSE Officer (permit now active) |
| Work permit rejected by Manager (final) | Submitting employee or HSE Officer (with rejection reason) |
| Work permit assigned to Employee by HSE Officer | Assigned employee |

**Channels**: an in-app notification (bell icon, web dashboard; in-app list,
mobile) for everything in the table, plus email for the higher-stakes ones
(account creation, email verification, password reset, payslip ready, work
permit approved/rejected) and a mobile push notification (FCM/APNs)
mirroring the in-app one.

**Web delivery mechanic**: since the dashboard is HTMX-only with no
websocket layer, the notification bell polls an endpoint (`hx-trigger="every
30s"`) that returns the unread count and a dropdown partial — simple and
consistent with the rest of the architecture, at the cost of a small delay
versus push.

**Mobile delivery**: a tapped push notification deep-links into the
relevant screen (e.g. a leave-approved notification opens that Leave
Request's detail).

Underlying model: `Notification(recipient: User, type, message,
related_object: GenericFK, is_read, created_at)`.

### 7.6 Report Generation / Export 

Available reports (role-gated, same as the sidebar in §1.2): Attendance
Summary, Leave Balance Report, HSE Man-Hours Report (§6.2), Work Permit/
Induction Compliance Report, Payroll Summary Report, Headcount/Turnover
Report.

User navigates to Reports → selects a report type → sets filters (date
range, department/site/project, employee) → selects format (PDF or CSV)
→ **Small reports** (single department, short date range): generated
synchronously, downloaded directly
→ **Large reports** (full-year payroll, all-department man-hours, etc.):
queued as a Celery task → user notified (§7.5) when ready → downloads via a
signed URL, the same pattern used for documents and payslips
→ A **Report History** list keeps previously generated reports accessible
for re-download within a retention window (e.g. 30 days) before the file/
signed URL expires

---

## Changelog

**v1.1** — Filled all ten gaps listed in v1.0's "[GAP] Missing Journey
Details" section:

1. Web Dashboard Navigation Structure → §1
2. Onboarding Flow → §3.1 (revised: added HR Admin self-registration with email confirmation before onboarding wizard)
3. Shift Assignment Flow → §3.7 "Assigning Shifts to Employees"
4. Attendance Dispute Flow → §3.6 "Reviewing Disputed Attendance Records" + §5.4
5. Bulk Employee Import → §3.5 "Bulk Employee Import"
6. Report Generation / Export → §7.6
7. Notification Flow → §7.5
8. Password Reset Flow → §7.4
9. Multi-site / Project Assignment → §3.11
10. Mobile App Onboarding → §5.1
