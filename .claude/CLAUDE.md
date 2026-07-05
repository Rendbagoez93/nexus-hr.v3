# Nexus — Centralized Employee Data Management SaaS

This file is always loaded when working in this repository. It describes the
product, the architecture decisions already made, and the conventions every
change must follow. For deep domain rules on a specific module (payroll math,
geofencing, HSE compliance, etc.) consult the `nexus-domain` skill — this file
stays high-level on purpose so it's fast to read on every turn.

## What Nexus is

Nexus is a SaaS Centralized Employee Data Management System for manufacturing,
construction, mining, and general office industries. **Employee is the
central entity** — every other module (Attendance, HSE, Payroll) hangs off
the Employee record rather than owning its own parallel identity. When you
add a field or a model anywhere in the codebase, ask "does this relate to an
Employee?" before inventing a new identity concept.

Four modules, sold as additive tiers on top of a mandatory Core:

| Module | Purpose | Tier |
|---|---|---|
| Core | Employee master data, departments, positions, documents, auth | Always included |
| Attendance & Leave | Mobile clock-in/out (GPS + photo), shifts, leave requests/approvals | Add-on |
| HSE + Man Hours | Violations, man-hour aggregation, induction, work permits, licenses | Add-on |
| Payroll | Payroll calculation, payslips, overtime, PPh 21, BPJS | Add-on |

Billing is **per active employee per month**, with each add-on module
increasing the per-employee rate for a company. This means almost every
model in the system is scoped to a `Company` (tenant), and feature access
must be gated by which modules that company's subscription includes — never
hardcode availability of Attendance/HSE/Payroll features.

## Two clients, one backend

- **Flutter mobile app**: the *only* surface for clock-in/clock-out, for
  everyone — employees, managers, and HR admins alike. There is no web
  equivalent for clocking in/out, and that's a deliberate product rule, not a
  gap. Never add a "clock in" button or endpoint usable from the web
  dashboard.
- **Web dashboard (Django templates + HTMX)**: administrative work only —
  Employee CRUD, payroll processing, HSE oversight, approvals, reporting.
  Server-rendered HTML with HTMX for partial updates; no SPA framework, no
  client-side state management. Vanilla CSS using custom properties (design
  tokens) for theming, vanilla JS only where HTMX attributes aren't enough.

Both clients are served by the same Django project. The Flutter app talks to
DRF JSON endpoints; the web dashboard is rendered server-side and talks to
the same underlying services, just through Django views instead of
serializers.

## Tech stack

- **Backend**: Python, Django + Django REST Framework
- **Database**: PostgreSQL
- **Mobile**: Flutter (consumes the DRF API only)
- **Web dashboard**: Django Templates + HTMX, vanilla CSS (design tokens), vanilla JS
- **Background/scheduled work**: payroll runs, man-hour aggregation, and
  license/permit expiry checks are periodic jobs — use whatever task runner
  is configured in this repo (check for Celery config or management commands
  under `apps/*/management/commands/` before assuming).

## Architecture: layered apps, not fat views or fat models

Every Django app in this project follows the same internal layering. This is
the main mechanism for satisfying "modular" and "readable" — logic always
lives in the same kind of file, so anyone (human or Claude) can find it
without searching:

```
apps/<module>/
├── models.py        # data shape only — fields, constraints, simple properties
├── selectors.py     # read queries — anything that fetches/filters data
├── services.py      # write logic — anything that mutates data or runs business rules
├── serializers.py   # internal serializers (not API layer)
├── views_web.py     # Django views for the HTMX dashboard — call services/selectors
├── urls_web.py      # HTMX dashboard URL routing
├── admin.py
└── tests/
```

API views and URLs live in `apps/apis/v1/<module>/`, separate from the
Django app:

```
apps/apis/v1/<module>/
├── __init__.py
├── views.py          # DRF viewsets/views — call services/selectors, no business logic
├── urls.py           # API URL routing
```

Rule of thumb: if a view, serializer, or model method has an `if` that
encodes a business rule (not just validation), that logic belongs in
`services.py` or `selectors.py`, not where you found the urge to write it.
This keeps views genuinely thin and testable in isolation from HTTP.

Suggested top-level layout:

```
nexus-hr.v2/
├── config/            # settings, root urls, asgi/wsgi
├── apps/
│   ├── shared/        # cross-module utilities, mixins, permissions, logging, utils
│   ├── companies/     # Company, SubscriptionPlan, CompanySubscription
│   ├── users/         # AuthUser, RefreshToken
│   ├── audit/         # AuditLog
│   ├── departments/    # Department, Position (stubs)
│   ├── documents/     # EmployeeDocument (stub)
│   ├── attendance/    # Attendance, Shift, LeaveRequest, LeaveBalance
│   ├── hse/           # Violation, ManHourEntry, Induction, WorkPermit, License
│   ├── payroll/       # PayrollRun, Payslip, Overtime, PPh21Bracket, BPJSRate
│   └── apis/
│       └── v1/
│           ├── companies/
│           ├── users/
│           ├── attendance/
│           ├── hse/
│           └── payroll/
├── templates/         # dashboard templates + HTMX partials
├── static/            # design-token CSS, vanilla JS
├── tests/             # shared test fixtures, conftest
└── docs/              # product, technical, and design documentation
```

`companies`, `users`, `audit` must never import from `attendance`, `hse`, `payroll`.
Those three depend on `companies` (for `Company`), `users` (for `AuthUser`), and
`audit` — never the reverse. If you find yourself importing "downward," the
model or logic is probably misplaced.

## Coding standards (non-negotiable for this project)

**Clean Code**
- Names say what something is or does — no abbreviations that need a
  comment to decode (`emp_mh_agg` → `employee_man_hour_aggregate`).
- Functions do one thing. If you need "and" to describe a function, split it.
- No magic numbers/strings — geofence radius, leave quotas, tax brackets,
  BPJS rates all go in `constants.py` or the database, never inline.
- Docstrings are mandatory on anything implementing a business rule
  (payroll math, leave accrual, geofence validation) — explain *why*, the
  code already shows *what*.

**Readability & Productivity**
- Type hints on every function signature.
- Prefer explicit, boring code over clever one-liners — this codebase is
  read far more often than it's written.
- Formatter/linter (black + ruff, or whatever this repo has configured) runs
  clean before any change is considered done.
- Early returns over deep nesting; guard clauses at the top of a function.

**Modular**
- Follow the models/selectors/services/serializers/views layering above —
  every time, no exceptions for "quick" features.
- Shared logic (pagination helpers, base permission classes, money/decimal
  helpers) lives in `apps/shared/`, not duplicated per app.
- A module should be deletable (in principle) without breaking `core`. If
  removing `payroll/` would break `attendance/`, that's a modularity bug.

**Imports at the top**
- All imports at the top of the file: standard library, then third-party
  (Django, DRF, etc.), then local app imports — each group separated by a
  blank line, alphabetized within the group. No inline `import` statements
  inside functions except to resolve a genuine circular import, and if you
  do that, leave a comment explaining why.

## Domain rules to keep in mind everywhere

- **Money is `Decimal`, never `float`.** Payroll, BPJS, and PPh 21 amounts
  must use `Decimal` end to end, including in serializers and templates.
- **"Active employee" is a billing-relevant status**, not just an
  employment status — changes to how employment status maps to "active for
  billing" need sign-off, since it changes what companies are charged.
  See the `nexus-domain` skill for the current definition.
- **Mobile-only actions need server-side enforcement, not just UI
  omission.** The web dashboard simply not showing a "clock in" button is
  not enough — the API permission layer must also reject clock-in/out
  requests that didn't come from the mobile client.
- **Every model that isn't truly global is tenant-scoped** (FK to
  `Company`, directly or via `Employee`). Forgetting tenant scoping on a
  queryset is a data-leak bug between companies, treat it as a security
  issue, not a feature bug.
- **Indonesian payroll/tax/labor specifics (PPh 21, BPJS, man-hour and HSE
  compliance definitions) live in the `nexus-domain` skill** — don't
  reimplement or guess at these from general knowledge, the rules are
  jurisdiction-specific and change with regulation updates.

## Design patterns in Nexus

Django and DRF already implement many classic design patterns naturally
(managers are Factory Method, serializers are Adapters, viewsets use
Template Method). Don't force additional abstraction layers where Django
idioms are clearer.

**Patterns that genuinely help** in this codebase:
- **Strategy** — PPh 21 calculation methods (TER vs. progressive annual)
- **Chain of Responsibility** — Attendance validation (mobile-only → geofence → induction → shift)
- **Builder** — Complex PayrollRun construction with optional components
- **Adapter** — Third-party API integration only (BPJS API, payment gateways)

**Patterns to avoid**:
- Singleton (breaks tenant isolation)
- Abstract factories (use Django managers instead)
- Command objects (unless you genuinely need undo/redo)
- Signal-based Observer for core business logic (use explicit service calls)

See `.claude/skills/design-patterns/nexus-patterns.md` for detailed
examples using real Nexus entities (Employee, Payroll, Attendance). Consult
the generic pattern references in `.claude/skills/design-patterns/references/`
when integrating external systems.

## Testing expectations

- `pytest-django` (or whatever test runner is configured) with
  `factory_boy`/fixtures for Employee, Company, and Subscription, since
  almost every test needs a tenant-scoped Employee to exist.
- Anything in `services.py` gets a unit test independent of HTTP — these are
  plain functions, test them as such.
- Payroll, BPJS, and PPh 21 calculations are tested against known worked
  examples (golden values), not just "it runs without error."
- Geofence and mobile-only enforcement logic gets explicit tests for the
  rejection path, not only the happy path.

## When you're not sure

If a request would blur Core/Attendance/HSE/Payroll boundaries, add a
write-path to the web dashboard for something mobile-only, or skip the
selectors/services layering "just this once" — pause and flag it rather than
guessing. These are the seams most likely to cause subscription-billing
bugs or tenant data leaks later.
