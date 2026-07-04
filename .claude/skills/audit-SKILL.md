---
name: nexus-audit
description: Audit the Nexus codebase against the rules documented in CLAUDE.md and the nexus-domain SKILL.md — find drift between what's documented and what's actually implemented, and check whether the test suite covers this domain's known-risk areas (PPh21/BPJS math, mobile-only clock-in, multi-tenant scoping, idempotent payroll runs, geofence boundaries, pytest marker/fixture hygiene). Trigger this whenever the user asks to "audit", "review against the docs", "check for drift", "is this implementation correct", or asks whether a module's tests are adequate before shipping. Also use proactively right after generating a non-trivial chunk of code or tests for a Nexus module, before calling it done — don't wait to be asked.
---

# Nexus audit

This skill is a **checklist-driven verification pass**, not a general code
review. It exists because `CLAUDE.md` and `nexus-domain` encode decisions
that are easy to implement correctly once and then silently violate later
(a new selector that forgets the `company` filter, a payroll helper that
creeps back to `float`, a test file that grew without anyone re-checking
markers). General code review won't catch these because they're not bad
code in isolation — they're code that disagrees with a decision made
elsewhere in the docs.

Two independent passes, run separately:

1. **Architecture audit** — does the implementation match `nexus-domain`?
2. **Test audit** — does the test suite actually exercise this domain's
   known failure modes, and is it organized the way the project's testing
   conventions say it should be?

Run whichever the user asks for, or both if they just say "audit the
codebase." Don't try to fix violations inline as you find them — report
first, then ask whether to fix.

## How to run either audit

1. Re-read `CLAUDE.md` and `nexus-domain/SKILL.md` first, even if you think
   you remember them — rules may have been edited since you last read them.
2. Identify which modules actually have code yet (don't audit Payroll if
   only Core exists — note it as "not yet implemented," not a failure).
3. Work through the relevant checklist table below top to bottom. For each
   row, find the actual file(s), and record one of:
   - **Pass** — rule is satisfied, cite file:line.
   - **Fail** — rule is violated, cite file:line and quote the offending
     line (paraphrase if it's more than a few words).
   - **Unclear** — couldn't verify from static reading (e.g. depends on
     runtime config) — say what would resolve it.
   - **N/A** — module doesn't exist yet.
4. Output a findings table, worst-first (Fail, then Unclear, then Pass),
   not in checklist order — the user wants violations at the top, not
   buried under a wall of passes.
5. For every Fail, suggest the fix but don't apply it without confirmation.

---

## Part 1 — Architecture audit

| # | Rule (source) | Where to look | How to check | Fail looks like |
|---|---|---|---|---|
| A1 | Every tenant-scoped manager/selector filters by `company` or `employee__company` | `apps/*/managers.py`, `apps/*/selectors.py`, any custom `get_queryset` | `grep -rn "def get_queryset\|class.*Manager\|class.*QuerySet" apps/` then check each result filters by company, directly or transitively | A queryset that returns rows across companies — e.g. `Employee.objects.filter(department=dept)` with no company filter |
| A2 | Tenant base manager/queryset in `apps/shared/` is actually used, not bypassed | Each app's `models.py` | `grep -rn "objects = \|class Meta" apps/*/models.py` — confirm tenant-scoped models use the shared base manager | A model defines its own plain `objects = models.Manager()` instead of the shared tenant-aware one |
| A3 | Feature gating uses `company.subscription.has_module(...)`, not ad hoc checks | Views, permission classes | `grep -rn "subscription\|has_module\|hse_enabled\|payroll_enabled" apps/` | A view checks `if company.has_hse_models` or similar instead of going through `has_module` |
| A4 | Clock-in/out rejects non-Flutter clients at **both** the permission class and the service layer | `apps/attendance/permissions.py`, `apps/attendance/services.py` | Open both files, confirm the same check exists in each independently | Permission class checks `X-Client-Type` but `clock_in()` itself doesn't, so any direct service call (e.g. from a future internal job) bypasses it |
| A5 | Clock-in rejects a missing photo outright, not a warning | `services.clock_in` | Read the function body | Photo absence is logged/flagged but the function still returns a saved `AttendanceRecord` |
| A6 | Geofence radius/coordinates are stored on `Company`/`Site`, not a constant | `apps/attendance/services.py`, settings files | `grep -rn "geofence\|radius\|GEOFENCE" apps/ config/` | A hardcoded `RADIUS_METERS = 200` instead of a field read from the company/site row |
| A7 | `LeaveBalance` is a ledger (accrual + deduction rows), not a single mutable int field | `apps/attendance/models.py` | Read the `LeaveBalance` model definition | A single `balance = IntegerField()` mutated in place instead of summed ledger entries |
| A8 | Leave approve/reject logic lives in `services.py`, reachable identically from HTMX view and any other caller | `apps/attendance/services.py` vs `views.py` | Check the view calls the service function rather than mutating `leave_request.status` directly | A view does `leave_request.status = "approved"; leave_request.save()` inline instead of calling `approve_leave_request(...)` |
| A9 | `Violation.severity` is a defined-choices field, not free text | `apps/hse/models.py` | Read the field definition | `severity = CharField(max_length=255)` with no `choices=` |
| A10 | Man-hour totals are computed from `ManHourEntry` via a selector, never stored as a running total on `Employee` | `apps/hse/models.py`, `apps/hse/selectors.py` | `grep -rn "total_man_hours\|man_hours" apps/` | `Employee.total_man_hours` exists as a stored/incrementing field |
| A11 | `employee_has_valid_induction(employee, site)` exists and is the single source of truth used by both clock-in gating and HSE reporting | `apps/hse/selectors.py` or `services.py` | `grep -rn "induction" apps/` — confirm one function, multiple call sites | Two separate ad hoc induction checks (one in attendance, one in reporting) that could drift apart |
| A12 | Expiring license/work-permit check is one reusable selector (`licenses_expiring_within(days)`), not duplicated per view | `apps/hse/selectors.py` | `grep -rn "expir" apps/hse/` | Same expiry-window logic re-implemented separately in a dashboard view and a notification job |
| A13 | PPh21 rates and BPJS rates come from `PPh21TerRate` / `BPJSRate` DB tables, never hardcoded Python constants | `apps/payroll/` | `grep -rn "0\.01\|0\.02\|0\.0[0-9]\|TER_CATEGORY\|PPH21_RATE" apps/payroll/*.py` | A dict or constant like `TER_RATES_CATEGORY_A = {...}` baked into code instead of a DB-backed lookup |
| A14 | Monthly PPh21 (TER) and the December/final-month annual recalculation are **separate** functions, not one function branching internally | `apps/payroll/services.py` | `grep -rn "def.*pph21\|def recalculate_annual" apps/payroll/services.py` | One `calculate_pph21(employee, month)` function with an `if month == 12` branch instead of a distinct `recalculate_annual_pph21` |
| A15 | Every value in the payroll calculation chain uses `Decimal`, never `float` | `apps/payroll/*.py`, serializers, templates | `grep -rn "float(" apps/payroll/` and check every `DecimalField` vs `FloatField` in serializers/models | Any `float(...)` cast or `FloatField` touching gross pay, BPJS, PPh21, or net pay |
| A16 | `PayrollRun` is idempotent — rerunning an already-processed period no-ops or requires explicit reprocess, never silently duplicates payslips | `apps/payroll/services.py`, `models.py` | Read `PayrollRun` status field and the run-creation function | A `run_payroll(company, period)` that always creates new `Payslip` rows with no check for an existing completed run |
| A17 | Salary ceilings (BPJS Kesehatan, JP) are configurable values tied to an effective date, not literals | `apps/payroll/models.py` | `grep -rn "12_000_000\|10_500_000\|ceiling" apps/payroll/` | A hardcoded ceiling number instead of a `BPJSRate`/ceiling row with `effective_date` |
| A18 | `AttendanceRecord` timestamps stored in UTC, resolved to site-local timezone only for display/shift logic | `apps/attendance/models.py`, settings | Check `USE_TZ`, check the field is `DateTimeField` (timezone-aware), check no `naive` comparisons | A naive datetime comparison across two sites, or `USE_TZ = False` |

---

## Part 2 — Test-suite audit

This checks **coverage of known-risk behavior**, not line/branch coverage
percentage. A module can have 90% coverage and still completely miss the
one test that matters (e.g. the geofence boundary edge case).

It also checks the project's own testing conventions — pytest marker
categorization and fixture scoping — stay consistent as the suite grows,
since that's an area you've been actively shaping in the requirements doc
and it's easy for new test files to drift from the convention silently.

### 2a. Domain-risk coverage checklist

| # | Required test | Where it should live | What "covered" means | What a gap looks like |
|---|---|---|---|---|
| T1 | PPh21 TER calculation against known worked examples | `apps/payroll/tests/test_pph21.py` | Test asserts against an accountant-verified or official-calculator golden value, not just "returns a Decimal" | A test that only checks `result > 0` or mocks the rate table entirely |
| T2 | December/final-month annual PPh21 recalculation reconciles against prior withheld tax | same | A test exercises `recalculate_annual_pph21` with multiple prior months' withholding and checks the credit is applied | No test calls `recalculate_annual_pph21` at all — only the monthly path is tested |
| T3 | BPJS calculations (Kesehatan, JHT, JP, JKK, JKM) against known rates, including ceiling behavior | `apps/payroll/tests/test_bpjs.py` | A test case specifically pushes salary above the ceiling and confirms the contribution caps correctly | Only sub-ceiling salaries are tested; the cap branch is unexercised |
| T4 | Mobile-only clock-in rejection | `apps/attendance/tests/test_permissions.py` or `test_clock_in.py` | A test sends a request with missing or wrong `X-Client-Type` and asserts rejection — at **both** the permission-class level and the service-function level (per A4) | Only the permission class is tested; `clock_in()` called directly in a test never gets a non-mobile `client_type` to reject |
| T5 | Missing-photo clock-in is rejected, not warned | `test_clock_in.py` | Test omits the photo and asserts an exception/4xx, not just a log assertion | Test passes `photo=None` and only checks a warning was logged |
| T6 | Geofence boundary conditions | `test_geofence.py` | Test cases at exactly the radius edge (and just inside/outside), plus a multi-site company to confirm the correct site's geofence is selected | Only "clearly inside" and "clearly outside" cases exist — the edge itself is untested |
| T7 | Cross-company data isolation (multi-tenancy leak test) | `apps/core/tests/test_tenancy.py` or per-app | Test creates two companies with overlapping data and asserts a query scoped to company A never returns company B's rows, for every tenant-scoped model | No test ever creates a second company — single-tenant test data can't catch a missing company filter |
| T8 | Payroll run idempotency | `apps/payroll/tests/test_payroll_run.py` | Test runs payroll for a period twice and asserts the second run no-ops or requires explicit reprocess, with no duplicate `Payslip` rows | Test only runs payroll once per test case — retry behavior is never exercised |
| T9 | Leave balance ledger correctness | `apps/attendance/tests/test_leave_balance.py` | Test asserts the balance is derived by summing ledger entries (accrual + deduction), and that approval creates the correct ledger entry | Test asserts on a mutated integer field directly, which would still pass even if A7 regressed |
| T10 | Induction gating | `apps/hse/tests/test_induction.py` | Test confirms `employee_has_valid_induction` blocks/flags correctly for an employee with no induction record, an expired one, and a valid one | Only the "valid" case is tested |
| T11 | License/work-permit expiry selector | `apps/hse/tests/test_licenses.py` | Test covers "expires within window," "already expired," and "not yet in window" | Only "already expired" is tested; the proactive "expiring soon" case is missed |

### 2b. Marker and fixture hygiene

Check this whenever new test files are added or the suite has grown since
the last audit — it answers "is the suite still organized the way we
decided it should be," separate from "does it cover the right things."

- **Marker categorization consistency**: confirm every test file's markers
  match your documented categories (check the current categorization
  scheme in the requirements doc before flagging — don't assume a specific
  scheme). Run `grep -rn "@pytest.mark\." apps/*/tests/` and check for:
  - Tests with no marker at all where the convention expects one.
  - A test marked e.g. `@pytest.mark.unit` that actually hits the database
    or makes a network call (mismatch between label and behavior, not just
    a missing label).
  - Marker spelling drift (`@pytest.mark.integration` vs
    `@pytest.mark.integration_test` used inconsistently across files).
- **Fixture scope correctness**: for each fixture in `conftest.py` files,
  confirm the declared `scope=` matches actual usage:
  - A `scope="function"` fixture that does expensive setup (e.g. spins up
    a full company + employees) when nothing in it is mutated per-test —
    candidate for `scope="module"` or `scope="session"`.
  - A `scope="session"`/`scope="module"` fixture whose object **is**
    mutated by individual tests — this is a correctness bug, not just a
    performance one, since state leaks between tests. Flag this as a Fail,
    not a suggestion.
  - Run `grep -rn "@pytest.fixture" apps/*/tests/conftest.py` and read each
    one's body to judge mutation, not just its name.

---

## Output format

Report findings as a table, worst severity first, then a one-line summary
count (e.g. "6 Fail, 2 Unclear, 14 Pass — Payroll module has the most
drift"). For each Fail, include: rule ID, file:line, one-sentence
description of the violation, and a suggested fix — but don't apply fixes
until the user confirms which ones to act on.