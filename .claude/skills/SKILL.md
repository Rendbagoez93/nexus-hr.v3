---
name: nexus-domain
description: Domain and architecture rules for building features inside the Nexus employee data management SaaS (Django + DRF + HTMX, PostgreSQL, Flutter mobile client). Consult this skill whenever you're implementing or modifying anything in the Core, Attendance & Leave, HSE + Man Hours, or Payroll modules — employee records, clock-in/out, GPS or photo attendance validation, shift or leave logic, violations, man-hour aggregation, induction/work-permit/license tracking, payroll runs, payslips, overtime, PPh 21, or BPJS deductions. Also use this whenever touching multi-tenant/Company scoping or the per-active-employee subscription billing logic. Always check this skill before writing payroll or tax calculation code — these are jurisdiction-specific and easy to get subtly wrong from general knowledge alone.
---

# Nexus domain rules

This skill covers the business logic specific to Nexus, beyond the general
coding conventions in `CLAUDE.md`. Read the relevant module section before
implementing, not the whole file end to end — sections are independent.

## Employee-centric data model

Every module's primary foreign key target is `Employee`, never a duplicate
identity concept. Before adding a model, check whether it should instead be
a field or related model on `Employee`.

| Module | Key entities (all FK to Employee, directly or via a join model) |
|---|---|
| Core | `Company`, `Employee`, `Department`, `Position`, `EmployeeDocument`, `User` |
| Attendance & Leave | `Shift`, `ShiftAssignment`, `AttendanceRecord`, `LeaveType`, `LeaveBalance`, `LeaveRequest` |
| HSE + Man Hours | `Violation`, `ManHourEntry`, `InductionRecord`, `WorkPermit`, `License` |
| Payroll | `PayrollRun`, `Payslip`, `OvertimeRecord`, `PPh21Category`, `PPh21TerRate`, `BPJSRate` |

`User` (auth) is a separate model from `Employee` and links one-to-one —
not every `User` is necessarily tied to an `Employee` (e.g. a company admin
account managing the subscription might not be), but every `Employee` who
needs system access has exactly one `User`.

## Multi-tenancy and billing

Nexus is shared-schema multi-tenant: every tenant-scoped model carries a
direct or indirect FK to `Company`. There is no schema-per-tenant — tenant
isolation is enforced entirely through querysets and permissions, so:

- Every default manager/selector must filter by `company` (or by `employee__company`).
  A selector that forgets this is a cross-company data leak, not a minor bug.
- Add a base queryset/manager in `apps/shared/` that requires a company filter to
  be explicit, rather than trusting every call site to remember it.

**Subscription model**: a `Company` has a `Subscription` with Core always
enabled and Attendance, HSE, and Payroll as independently toggleable add-on
modules. Billing is `active_employee_count × (core_rate + sum of enabled module rates)`,
charged monthly. Two things need an explicit, documented decision before you
implement billing logic (don't guess silently):

1. **What counts as "active" for billing** — e.g. employment status is
   `active` as of the billing cycle date, vs. average headcount across the
   period. Pick one, document it next to the `Subscription`/`BillingCycle`
   model, and keep it consistent with how "active" is used for HSE/payroll
   eligibility elsewhere.
2. **What happens mid-cycle** — an employee added or terminated mid-month
   either prorates or doesn't. Flag this for the user rather than assuming.

Gate feature access with a permission/decorator that checks
`company.subscription.has_module("hse")` rather than checking model
existence or scattering `if` checks through views.

## Attendance & Leave

**Mobile-only clock-in/out is a server-side rule, not a UI choice.** The
DRF endpoint for clock-in/clock-out must reject the request unless it can
verify it came from the Flutter app — don't rely on "the web dashboard just
doesn't have this button." A reasonable enforcement pattern:

```python
# apps/attendance/permissions.py
class IsMobileClient(BasePermission):
    """Clock-in/out is mobile-only for every role — employee, manager, and
    HR admin alike. Reject anything that isn't the Flutter client, even if
    the requester is otherwise authorized to view/approve attendance."""

    def has_permission(self, request, view) -> bool:
        client = request.headers.get("X-Client-Type")
        return client == "flutter-mobile"
```

Pair this with a service-layer check, not just the permission class, since
permission classes are easy to forget to attach to a new endpoint:

```python
# apps/attendance/services.py
def clock_in(*, employee: Employee, latitude: float, longitude: float,
             photo: UploadedFile, client_type: str) -> AttendanceRecord:
    if client_type != "flutter-mobile":
        raise PermissionDeniedError("Clock-in is mobile-only.")
    if not is_within_geofence(employee.company, latitude, longitude):
        raise OutsideGeofenceError(...)
    # photo is required, not optional — store it, don't just validate presence
    ...
```

**Geofencing**: validate against the company's (or site's, if a company has
multiple sites) registered coordinates and an allowed radius — store both on
`Company`/`Site`, not as a hardcoded constant, since radius reasonably
differs between an office and a mine site. Treat GPS coordinates as
advisory, not cryptographically trustworthy — they can be spoofed on a
rooted/jailbroken device — so don't make geofencing the *only* safeguard
where the business actually cares (e.g. payroll-affecting attendance might
also want photo + timestamp server-side checks).

**Photo requirement**: store the photo and its capture timestamp/EXIF
alongside the `AttendanceRecord`, and treat a missing photo as a rejected
clock-in, not a clock-in with a warning.

**Leave**: model `LeaveBalance` as a ledger (accrual and deduction entries),
not a single mutable integer — it makes audit and "why does this employee
have this balance" debugging possible, and matches how leave actually
accrues over time (often monthly accrual, not a yearly lump grant).
`LeaveRequest` approval should go through `services.py` so the same
approve/reject logic is reachable identically from the HTMX dashboard and
any future automation, not duplicated in the view.

## HSE + Man Hours

- **Violations** need a severity scale (e.g. minor/major/critical) as a
  proper field with defined values, not free text — HSE reporting depends
  on being able to aggregate by severity.
- **Man-hour aggregation** should be computed from raw `ManHourEntry` rows
  (one row per employee per shift/work period) via a selector, not stored
  as a running total on `Employee` — running totals drift and are hard to
  audit or recompute after a correction.
- **Induction** gates site access: a service function like
  `employee_has_valid_induction(employee, site)` should be the single
  source of truth, used both to block clock-in at a site (if the business
  wants that) and to flag non-compliant employees in HSE reporting.
- **Work permits and licenses** have expiry dates that matter operationally
  — build the "expiring soon / expired" check as a reusable selector
  (`licenses_expiring_within(days)`) so it can back a dashboard view, a
  scheduled notification job, and a report without three implementations.

## Payroll

**Calculation order matters and should be a single documented service
function**, not assembled ad hoc in a view or template:

```
gross pay = base salary + allowances + overtime pay
taxable income = gross pay − BPJS employee contributions − occupational cost deduction
PPh 21 = computed per the TER method below, on taxable income
net pay = gross pay − PPh 21 − BPJS employee contributions − other deductions
```

Always use `Decimal`, never `float`, for every value in this chain,
including in serializers (`DecimalField`) and templates.

**PPh 21 — TER (Tarif Efektif Rata-rata) method.** Since the PMK 168/2023 /
PP 58/2023 reform, monthly PPh 21 withholding for permanent employees uses a
simplified effective-rate table looked up by PTKP status and monthly gross
income, rather than computing progressive brackets every month:

- Employees are bucketed into **TER category A** (TK/0, TK/1, K/0),
  **category B** (TK/2, TK/3, K/1, K/2), or **category C** (K/3) based on
  marital/dependent status (PTKP status).
- Each category has its own table mapping a monthly gross-income range to an
  effective percentage. Look this up from a `PPh21TerRate` table in the
  database (category, income range, rate) — **do not hardcode the
  percentage table as Python constants.** These rates and brackets come
  from government regulation and have changed before; storing them as data
  means an update is a data migration, not a code deploy, and means the
  rates the system is using are auditable.
- December (or an employee's final month if they leave mid-year) is
  recalculated using the **annual progressive rates** under Article 17 of
  the income tax law (currently 5%/15%/25%/30%/35% across income bands per
  UU HPP 7/2021) against full-year taxable income, with prior months'
  withheld tax credited — this reconciles the simplified monthly TER
  estimate against the actual annual liability. Implement this as a
  distinct `recalculate_annual_pph21(employee, year)` function, don't try
  to bend the monthly TER function to also handle December.
- Non-employee/freelance payments (if Nexus ever needs to support them) use
  a different base (50% of gross as the taxable base) and the progressive
  Article 17 rate directly — keep this as a clearly separate code path,
  don't merge it into the permanent-employee TER function.

Whoever owns this module should confirm current TER tables and Article 17
brackets against the latest PMK/PP before going live and whenever Indonesian
tax regulations change — this skill describes the *method*, not a frozen
set of numbers to trust indefinitely.

**BPJS contributions** (reference rates — store as configurable `BPJSRate`
rows, not constants, for the same reason as PPh 21):

| Program | Employee | Employer | Notes |
|---|---|---|---|
| BPJS Kesehatan | 1% | 4% | Capped at a salary ceiling (~Rp12,000,000/month) |
| JHT (old age) | 2% | 3.7% | Total 5.7% of wage |
| JP (pension) | 1% | 2% | Capped at a salary ceiling reviewed periodically (~Rp10.5M/month as of 2026) |
| JKK (work accident) | — | 0.24%–1.74% | Employer-only, varies by industry risk category — relevant here since manufacturing/construction/mining sit at different risk tiers |
| JKM (death) | — | 0.3% | Employer-only |
| JKP (job loss) | — | — | Funded by government + JKK/JKM recomposition, not an extra payroll deduction |

Salary ceilings change periodically — store them as configurable values tied
to an effective date, not literals, so historical payroll runs still
recompute correctly with the rate that was in force at the time.

**Idempotent payroll runs**: a `PayrollRun` for a given company and period
should be safe to retry without double-paying anyone — model it so
generating payslips for an already-processed period either no-ops or
requires an explicit "reprocess" action, not a silent duplicate run.

## Code patterns to follow

**Service function shape** — keyword-only arguments, explicit return type,
docstring stating the business rule:

```python
def approve_leave_request(*, leave_request: LeaveRequest, approver: Employee) -> LeaveRequest:
    """Approve a leave request and deduct the balance ledger entry.

    Only a manager in the requester's department, or HR admin, may approve.
    Raises PermissionDeniedError otherwise.
    """
    if not can_approve_leave(approver=approver, leave_request=leave_request):
        raise PermissionDeniedError(...)
    leave_request.status = LeaveRequest.Status.APPROVED
    leave_request.save(update_fields=["status"])
    create_leave_balance_entry(...)
    return leave_request
```

**DRF view for the mobile API** — thin, delegates to services/selectors:

```python
class AttendanceClockInView(APIView):
    permission_classes = [IsAuthenticated, IsMobileClient]

    def post(self, request: Request) -> Response:
        serializer = ClockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = clock_in(employee=request.user.employee,
                           client_type=request.headers.get("X-Client-Type"),
                           **serializer.validated_data)
        return Response(AttendanceRecordSerializer(record).data, status=201)
```

**HTMX dashboard view** — same selectors/services, returns a partial
template when the request is an HTMX request:

```python
def leave_request_list(request: HttpRequest) -> HttpResponse:
    requests = pending_leave_requests_for(approver=request.user.employee)
    template = "attendance/_leave_request_table.html" if request.htmx \
        else "attendance/leave_request_page.html"
    return render(request, template, {"requests": requests})
```

## Pitfalls specific to this domain

- **Timezones**: manufacturing/construction/mining sites can span multiple
  timezones even within one company. Store `AttendanceRecord` timestamps in
  UTC and resolve to the site's local timezone for display and shift-window
  logic — never compare raw naive datetimes across sites.
- **Money as float** is the single most common way payroll numbers go subtly
  wrong; grep for `float` near payroll/BPJS/PPh21 code in review.
- **GPS spoofing**: don't let geofencing alone gate something financially
  significant (e.g. overtime eligibility) without a secondary signal (photo,
  timestamp consistency).
- **Double payroll runs** from a retried request or a re-clicked button are
  an idempotency bug, not a user error — guard at the service layer.
- **Expired licenses/work permits silently going unnoticed** until an audit
  is itself an HSE compliance failure — the expiry selectors should back a
  proactive check, not just an on-demand report.

## Testing this domain

- Test PPh 21 and BPJS calculations against known worked examples (golden
  values from official calculators or accountant-verified cases), not just
  "the function returns a number."
- Test the mobile-only rejection path for clock-in/out explicitly — a
  request with a missing or wrong `X-Client-Type` header must fail, and
  that's as important to test as the success path.
- Test geofence boundary conditions (exactly at the radius edge) and a
  multi-site company to make sure the right site's geofence is used.
- Test that a second payroll run for an already-processed period doesn't
  duplicate payslips.
