# Nexus HR — Web Dashboard Template Design Guide

**Version**: 1.0 (Initial Draft)
**Date**: July 21, 2026
**Status**: Planning — Implementation Pending
**Scope**: Web Dashboard only (Django Templates + HTMX, vanilla CSS via design tokens, vanilla JS)

> Companion to `ui-ux-brief.md` (the established dark-theme design system). This
> document focuses on **the application chrome** — the data-heavy interfaces HR
> Admins and Managers use every day to operate the platform: rosters, drawers,
> density controls, shift-aware views. It is the bridge between the visual
> language and the operational screens.

---

## 1. How to Read This Guide

This is a **planning document only**. No HTML, CSS, or JS is shipped here.

The guide covers:

1. **Design Philosophy** — what "Nexus" feels like as an *operational* product
2. **Layout Architecture** — the shared chrome (sidebar, top bar, shell)
3. **Key Layout Features** — Density Toggles, Slide-over Drawers
4. **Color Palette Strategy** — authoritative, professional, clean
5. **Typography** — font choices and the type scale for data screens
6. **Component Catalog** — tables, drawers, command palette, etc.
7. **Shift-Aware UI** — how the interface reflects the live state of the workforce
8. **Data Contracts** — the API surfaces each view consumes
9. **Accessibility** — keyboard, contrast, motion
10. **Implementation Conventions** — file naming, class naming, htmx patterns

For pixel-level styling primitives (colors as hex, type sizes as px, shadows as
rgba) see [docs/ui-ux-brief.md](ui-ux-brief.md). This guide assumes those tokens
exist as CSS custom properties on `:root` and references them by name
(`--color-primary`, `--space-md`, `--radius-md`, etc.) — never inline.

---

## 2. Design Philosophy — "Informative Command Center"

### 2.1 The Mental Model

Nexus is not a marketing site, and it is not a lightweight CRUD admin. It is a
**command center** for an HR operations team managing thousands of field
workers across construction, manufacturing, mining, and office sites.

The dashboard must:

| Feel | Like | Not like |
|------|------|----------|
| Authoritative | Air Traffic Control console | Consumer SaaS landing page |
| Dense | Excel at 110% zoom on a 27" monitor | Cardy mobile-first flow |
| Calm | Bloomberg Terminal in dark mode | Flashy dashboard with rainbow charts |
| Instant | Sub-200ms interactions on cached rows | Heavy SPA route transitions |

The interface must always answer three questions at a glance:

1. **Who is on shift right now?** (status, geofence, clock-in)
2. **Who needs me?** (pending approvals, expired inductions, overdue tasks)
3. **What changed since I last looked?** (audit-trail style feed)

### 2.2 Core Principles (Ranked)

1. **Information Density Without Chaos** — show 30–50 rows by default; never
   paginate below 25 just to look "clean".
2. **Predictable Affordances** — every table row looks like a row, every
   drawer looks like a drawer, no creative reinterpretations of basic UI.
3. **Status Over Decoration** — status labels and icons convey state. No
   decorative emoji, no motivational illustrations, no animated mascots.
4. **Read > Write > Edit Hierarchy** — the dashboard is optimized for *looking*
   at data. Editing is precise, modal, and one-field-at-a-time when possible.
5. **Module-Gated Visibility** — Attendance, HSE, and Payroll surfaces are
   only rendered if the company's subscription tier includes them. The shell
   itself, and the Core (Employee) screen, are always visible.
6. **Mobile is Not a Goal** — the web dashboard is for desk-based HR Admins.
   Anything that needs to happen on a job site happens on the Flutter app.
   Don't waste layout cycles shrinking the dashboard to 360px.

### 2.3 The "Shift-Aware" Posture

Most HR products are "date-aware" — they default to today. Nexus must be
**shift-aware**: at any moment, an admin's mental model is
*"who is on shift right now, and what is happening on that shift?"*.

The interface reflects this by:

- Defaulting to the **current shift window** (e.g. Site A morning shift
  06:00–14:00) on every page that has a time dimension, not just today's date.
- Showing a **live clock** in the top bar with the shift label and remaining
  time, so the admin always knows what window they're looking at.
- Highlighting rows that are **between clock-in and clock-out right now** with
  a subtle live indicator (not animation — a left-edge accent bar in
  `--color-success`).
- Surfacing **shift transitions** as soft banners ("Shift handover in 12
  minutes — 14 employees still clocked in from morning shift").

---

## 3. Backend Context (What We Are Designing Against)

The dashboard consumes JSON from `apps/apis/v1/` driven by Django + DRF.
Understanding the data shape determines the column choices in every table.

### 3.1 Data Model Summary

```
Company ──┬── AuthUser (role: platform_admin / hr_admin / manager /
          │                   employee / hse_officer)
          │
          ├── Department (self-referencing parent, code per company)
          │       └── Position (level, salary band)
          │
          ├── Employee ── emp_number (NXS-0001), status, employment_type,
          │              join_date, base_salary, direct_manager
          │       └── EmployeeDocument (KTP, NPWP, Contract, Ijazah, SIM,
          │                            Sertifikat, Other) — private S3 key,
          │                            signed URL on retrieve
          │
          ├── Subscription / SubscriptionPlan (has_attendance, has_hse,
          │                                   has_payroll flags)
          │
          └── (future) Attendance, Shift, LeaveRequest, Violation,
              ManHourEntry, Induction, WorkPermit, PayrollRun, Payslip
```

**Source-of-truth entities**:
[apps/employees/models.py](../apps/employees/models.py),
[apps/documents/models.py](../apps/documents/models.py),
[apps/departments/models.py](../apps/departments/models.py),
[apps/companies/models.py](../apps/companies/models.py)

### 3.2 Authentication Flow

JWT-based — bearer token + refresh token. See
[apps/apis/v1/auth/views.py](../apps/apis/v1/auth/views.py) and
[apps/shared/middleware/tenant_middleware.py](../apps/shared/middleware/tenant_middleware.py).

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/login` | POST | Obtain access + refresh tokens |
| `/api/v1/auth/token/refresh` | POST | Refresh access token |
| `/api/v1/auth/logout` | POST | Blacklist refresh token |
| `/api/v1/auth/password/change` | POST | Change own password |

JWT carries `user_id`, `company_id`, `role`. TenantMiddleware attaches
`request.company_id` so every downstream query is implicitly tenant-scoped.

### 3.3 The API Surfaces the Dashboard Consumes

#### Core — Employees
[apps/apis/v1/employees/views.py](../apps/apis/v1/employees/views.py),
[apps/apis/v1/employees/serializers.py](../apps/apis/v1/employees/serializers.py),
[apps/apis/v1/employees/urls.py](../apps/apis/v1/employees/urls.py)

| Method | Path | Permission | Used by |
|--------|------|-----------|---------|
| GET | `/api/v1/employees/` | Authenticated | Site Roster table |
| POST | `/api/v1/employees/` | HR Admin | New Employee wizard |
| GET | `/api/v1/employees/{id}/` | Owner or HR Admin | Slide-over Drawer (right panel) |
| PATCH | `/api/v1/employees/{id}/` | HR Admin | Drawer inline edit |
| POST | `/api/v1/employees/{id}/deactivate/` | HR Admin | Drawer "Deactivate" action |
| GET | `/api/v1/me/` | Authenticated | Top-bar identity chip |

**Query params for list**: `status`, `department_id`, `is_active`.
**Pagination**: default 25, max 100 — `NexusPaginator`
([apps/shared/utils/pagination.py](../apps/shared/utils/pagination.py)).

#### Documents
[apps/apis/v1/documents/views.py](../apps/apis/v1/documents/views.py)

| Method | Path | Permission |
|--------|------|-----------|
| GET | `/api/v1/employees/{employee_pk}/documents/` | Owner or HR Admin |
| POST | `/api/v1/employees/{employee_pk}/documents/` | HR Admin (multipart) |
| GET | `/api/v1/employees/{employee_pk}/documents/{id}/` | Owner or HR Admin (returns signed URL) |
| PATCH | `/api/v1/employees/{employee_pk}/documents/{id}/` | HR Admin |
| DELETE | `/api/v1/employees/{employee_pk}/documents/{id}/` | HR Admin (soft) |

#### Departments & Positions
[apps/apis/v1/departments/views.py](../apps/apis/v1/departments/views.py)

| Method | Path | Used by |
|--------|------|---------|
| GET | `/api/v1/departments/` | Department filter, sidebar tree |
| GET | `/api/v1/departments/tree/` | Org-chart view |
| GET | `/api/v1/positions/` | Position dropdown in employee form |

#### Future (stubs only — design slot reserved)

The dashboard chrome **reserves nav slots** for Attendance, HSE, and Payroll
but only renders the entries if the active company's subscription has the
matching module flag (see [apps/shared/permissions.py](../apps/shared/permissions.py) →
`HasModuleAccess`). When a tenant lacks the module, the nav entry is replaced
by a "Module not in your plan — Upgrade" link.

### 3.4 Standard Response Envelopes

The dashboard uses HTMX for partial updates and vanilla `fetch` for first-paint
JSON loads. Both must handle three envelope shapes consistently:

```jsonc
// Paginated list — { count, next, previous, results: [...] }
{ "count": 150, "next": "...", "previous": null, "results": [/* rows */] }

// Single resource — { data: { ... } }
{ "data": { "id": "uuid", "emp_number": "NXS-0001", ... } }

// Action confirmation — { message: "..." }
{ "message": "Employee deactivated successfully." }

// Error envelope — used by all 4xx/5xx responses
{ "error": "validation_error", "message": "...", "status": 400, "details": {} }
```

These are defined in
[docs/technical-requirement-document.md](technical-requirement-document.md) §3.
The dashboard's JS layer treats these shapes as the **contract**; any change
to them requires updating both the API and the fetch wrappers in the same PR.

---

## 4. Layout Architecture — The Application Shell

### 4.1 Top-Level Anatomy

The application shell is the wrapper around every authenticated screen
(login is a separate, chromeless layout).

#### Container Width

Per [docs/ui-ux-brief.md §6.1](ui-ux-brief.md), the Nexus dashboard uses the
**`.container`** class with:

- **Max-width**: `1200px`, centered, with `24px` horizontal padding.
- Never apply width constraints to a `<section>` directly — wrap content in
  `.container` so the rule has a single source of truth.
- Tables and the site roster live inside the same `.container`, even when
  that means a horizontal scrollbar on viewports < 1200px. **Do not** widen
  the container for tables — wider tables look untidy and break
  predictability across screens.

#### Layout Primitives (Grid vs. Flexbox)

Per [docs/ui-ux-brief.md §6](ui-ux-brief.md), the layout primitives have
fixed roles:

- **CSS Grid** is mandatory for any **multi-column** content grid:
  page-header split, stat tile grids, drawer tab grid, table toolbar split.
- **Flexbox** is for **single-axis alignment only**: top-bar items, sidebar
  nav rows, list items inside a card, label groups.
- Mixing roles (a `display: grid` row whose only columns are aligned
  one-axis) is a smell — switch to flexbox.

These rules apply to the dashboard as-written. New components must follow
them from the first commit, not retrofitted later.

```
┌──────────────────────────────────────────────────────────────────────┐
│  TopBar (56px, fixed)                                                │
│  [Logo + tenant name]   [Global Search]   [Shift Clock]   [User ▼]  │
├──────────────┬───────────────────────────────────────────────────────┤
│              │                                                       │
│  Sidebar     │   Page Header (sticky within content, breadcrumb +    │
│  (240px,     │   page title + primary action)                        │
│  collapsible │                                                       │
│  to 64px)    │   ┌─ .container (max-width: 1200px) ───────────┐    │
│              │   │   Page Content (table, drawer, form, etc.) │    │
│  • Dashboard │   │                                             │    │
│  • Employees │   │   When a drawer is open, the main content   │    │
│  • Attendance│   │   remains visible; the drawer overlays from  │    │
│  • HSE       │   │   the right edge.                           │    │
│  • Payroll   │   │                                             │    │
│  • Settings  │   └─────────────────────────────────────────────┘    │
│              │                                                       │
└──────────────┴───────────────────────────────────────────────────────┘
```

### 4.2 Sidebar — Persistent Navigation

- **Default width**: 240px. **Collapsed width**: 64px (icon-only). The
  collapse state is persisted to `localStorage` per browser, not per session,
  so the admin's preference survives a hard refresh.
- **Width transition**: 200ms ease on collapse/expand. Iconography must look
  correct at both sizes — never rely on text labels being readable when
  collapsed.
- **Active item indicator**: 3px vertical accent on the left edge in
  `--color-primary`, plus a subtle `--color-bg-card-2` background on the
  full row. Never use only colour.
- **Section headers** ("CORE", "ADD-ONS") — `12px / 700 / 0.05em / --color-text-subtle`.
  Hide section headers when the sidebar is collapsed.
- **Module-gated entries**: a tier indicator on the right side of the item,
  `--color-warning` background with the label "ADD-ON" — when the company's
  subscription doesn't include the module, clicking opens an upgrade dialog
  rather than navigating to the page.

### 4.3 TopBar — Global Context

The top bar is the same on every screen and contains, in order:

| Slot | Element | Data Source |
|------|---------|-------------|
| Left | Tenant logo + company name (truncate at 220px) | `request.user.company.name` |
| Center | Global search input (cmd-K focusable) | `/api/v1/employees/?search=` + `/api/v1/departments/` |
| Right-of-center | Shift Clock (see §7.2) | Server-rendered with timezone from `Company` |
| Far right | Notifications icon + User menu | `/api/v1/me/` |

**Background**: `--color-bg-card-2` with a 1px bottom border in
`--color-border`. **Sticky**: `position: sticky; top: 0; z-index: 50`.

The top bar never scrolls away — losing the global search and identity chip
to a scroll is a UX failure mode that creates friction in a dense data app.

### 4.4 Page Header Pattern

Below the top bar and above the page content, every page renders a
**page header band** with:

1. Breadcrumb (sentence case, `--color-text-subtle`)
2. H1 page title (24px / 700 / sentence case)
3. Sub-description (1 sentence, `--color-text-muted`)
4. Primary action button (one per page, right-aligned)

If the page needs secondary actions (export, bulk-update), they live in a
small icon-button cluster to the left of the primary action — never inline
with the title.

---

## 5. Key Layout Features

### 5.1 Dense Data Tables with Density Toggles

#### 5.1.1 The Three Density Modes

The single most important interaction on the dashboard. Admins working with
thousands of field workers need to choose how much vertical real estate they
want to spend per row.

| Mode | Row Height | Use | Padding (vertical) | Font | Avatar | Icon Button |
|------|-----------|-----|--------------------|------|--------|-------------|
| **Compact** | 36px | Scanning 500+ rows in triage mode | 6px | 13px / 500 | Hidden (initials in line) | Icon-only, square 28px |
| **Standard** (default) | 52px | Day-to-day operations | 10px | 14px / 500 | 32px circle, initials | Icon + tooltip, square 32px |
| **Comfortable** | 72px | Onboarding review, audit mode | 16px | 15px / 400 | 40px circle, photo if available | Icon + label |

The toggle is a three-state segmented control in the table toolbar:

```
[ Compact │ Standard │ Comfortable ]   Showing 1–25 of 1,247 employees
```

The selected mode is persisted to `localStorage` under
`nexus.tableDensity` (default `standard`). On page load, JS reads the value
before first render so there's no flash of wrong-density content.

#### 5.1.2 Table Anatomy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Toolbar:  [☐ Select all]   [🔍 Search]  [Filter ▾]  [Density ▾] [⚙ Columns]│
├─────────────────────────────────────────────────────────────────────────────┤
│ ☐ │  NXS-0001  │ John Doe        │ Engineering │ Software Eng │ Active │ ⋯  │
│   │  John      │ john@nexus.test │ (ENG)       │ Staff        │ ●      │    │
│ ☐ │  NXS-0002  │ Jane Smith      │ Operations  │ Field Super. │ Active │ ⋯  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Footer:   [Bulk actions ▼]   « 1 2 3 ... 50 »   1–25 of 1,247  [25▾]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Zone | Standard Mode | Compact Mode | Comfortable Mode |
|------|--------------|--------------|------------------|
| Row padding-y | 10px | 6px | 16px |
| Row padding-x | 16px | 12px | 20px |
| Font size | 14px | 13px | 15px |
| Avatar | 32px | hidden | 40px |
| Border between rows | `--color-border` (1px) | Same | Same |
| Zebra striping | optional, low contrast | never | optional |
| Hover background | `--color-bg-card-2` | same | same |
| Active-row background | `--color-primary` @ 8% opacity | same | same |

**Zebra striping** is off by default in Standard and Comfortable; it's a
considered visual choice that competes with row hover. Only enable it in
Compact mode if scanning tests show measurable benefit.

#### 5.1.3 Column Conventions

| Column type | Behaviour |
|-------------|-----------|
| Identifier (`emp_number`) | Monospace-feeling numerals, 13px, `--color-text-subtle` |
| Name (`first_name + last_name`) | `--color-text`, weight 500; click target opens the drawer |
| Status (`status`, `employment_type`) | Status label, see §5.1.4 |
| Money (`base_salary`) | Right-aligned, tabular numerals, locale-formatted (Rp 10.000.000) |
| Date (`join_date`) | `--color-text-muted`, ISO short format (`2024-03-15`) |
| Foreign key (department, position) | `--color-text-muted`, link to detail in future |
| Action | Icon-only, right-aligned, opens row menu (Edit, View Documents, Deactivate) |

**Column reordering and visibility** must be supported via a "Columns" dropdown
in the toolbar. Persist per-user, per-table to `localStorage` under
`nexus.columns.<table-name>`. Default column set is documented per screen in
the [Component Catalog](#8-component-catalog).

#### 5.1.4 Status Label System

Status is always colour + label + (optional) icon. Never colour alone
([WCAG 1.4.1](https://www.w3.org/WAI/WCAG21/Understanding/use-of-color.html)).

| State | Background | Text | Icon |
|-------|-----------|------|------|
| Active / On Shift | `--color-success` @ 15% | `--color-success` lighter tone | ● filled dot |
| Probation / On Leave | `--color-primary` @ 15% | `--color-primary-lt` | ◐ half dot |
| Pending / Expiring Soon | `--color-warning` @ 15% | `--color-warning` lighter tone | ▲ triangle |
| Inactive / Resigned | `--color-text-subtle` @ 15% | `--color-text-muted` | ○ outlined dot |
| Terminated / Rejected | `--color-danger` @ 15% | `--color-danger` lighter tone | ✕ cross |
| Verified document | `--color-success` @ 15% | `--color-success` lighter tone | ✓ check |

Label shape: `border-radius: 999px`, vertical padding 2px, horizontal padding
8px, font 11px / 600 / `0.04em` letter-spacing. Always uppercase in the label
body — `Active` not `active`.

#### 5.1.5 Row Interactions

- **Single click on the row body** → opens the slide-over drawer (§5.2).
- **Single click on a checkbox** → selects the row (does not open drawer).
- **Single click on a hyperlink within the row** → follows the link, no drawer.
- **Cmd/Ctrl-click on a row** → opens in a new tab (full employee detail page).
- **Right-click on a row** → context menu (Edit, View Documents, Deactivate,
  Copy emp_number, Open in new tab). Don't rely on this — also expose the
  menu in the trailing row-action icon.

The drawer-vs-detail-page split mirrors the trade-off in
[docs/ui-ux-brief.md](ui-ux-brief.md): drawer for **look-and-act**,
full page for **deep work** (audit history, document viewer, payroll history).

#### 5.1.6 Inline Cell Editing (Optional, V2)

Some cells (status, employment_type, department) should support inline
editing on a double-click for HR Admins. **Not** in scope for the initial
release — start with drawer-based editing and only adopt inline editing if
user research shows the round trip is a measured pain point.

### 5.2 Split View / Slide-over Drawers

#### 5.2.1 When to Use a Drawer vs. a Page

| Use a Drawer when… | Use a Full Page when… |
|-------------------|----------------------|
| The user wants to glance at one record while keeping the list in view | The record requires focus and several sub-flows |
| The action is read-mostly with one or two quick edits | The action is a multi-step wizard |
| The user is triaging — looking at many records in sequence | The user is doing deep work on a single record |
| Examples: site roster → employee profile, leave request → approver detail | Examples: payroll run setup, document viewer, induction form |

#### 5.2.2 Drawer Anatomy

```
                                      ┌───────────────────────────────────┐
                                      │ [×]  John Doe                      │
                                      │       NXS-0001 · Software Engineer │
                                      ├───────────────────────────────────┤
                                      │ [Profile] [Documents] [Shifts] ... │ ← tab bar
                                      ├───────────────────────────────────┤
                                      │                                     │
                                      │  [Active content tab]              │
                                      │                                     │
                                      │  • Identity card                   │
                                      │  • Employment card                 │
                                      │  • Direct reports card             │
                                      │  • Recent activity card           │
                                      │                                     │
                                      │  ... scrollable content ...        │
                                      │                                     │
                                      ├───────────────────────────────────┤
                                      │ [Deactivate]    [Edit Details]    │ ← sticky footer
                                      └───────────────────────────────────┘
```

#### 5.2.3 Dimensions & Behaviour

| Aspect | Value | Notes |
|--------|-------|-------|
| Width | 480px (default), 640px (wide), 360px (compact) | Configurable per drawer type |
| Height | 100vh | Always full-height |
| Slide direction | From right to left (LTR locales) | RTL mirrors the direction |
| Overlay | None — the main content stays visible, dimmed to 60% with `--color-bg` tint | The list is still the primary focus |
| Animation | `translateX(100%) → translateX(0)`, 220ms ease-out on open; 180ms ease-in on close | Matches [docs/ui-ux-brief.md](ui-ux-brief.md) §9 motion budget |
| Backdrop click | Closes the drawer (unless the form is dirty — confirm first) | Save unsaved changes prompt |
| Esc key | Closes the drawer (same dirty-form guard) | |
| Focus trap | First focusable element inside the drawer on open | Restores focus to the triggering row on close |
| URL sync | `?employee={id}` query param so the drawer state is bookmarkable and back-button works | |

#### 5.2.4 Drawer Tab Pattern

Each row's drawer has 4–6 tabs depending on the entity and the company's
active modules:

| Tab | Always? | Content |
|-----|---------|---------|
| Profile | ✓ | Identity, employment, salary, manager chain, audit |
| Documents | ✓ | All `EmployeeDocument` rows with expiry status, upload control |
| Shifts | If Attendance module | Current shift, next shift, recent shift history |
| Leave | If Attendance module | Leave balance, recent requests, pending requests |
| HSE | If HSE module | Valid inductions, open violations, man-hours MTD |
| Payroll | If Payroll module | Latest payslip, YTD totals, base salary band check |

Tabs are rendered server-side on the first open (full HTML in the drawer
body), then swapped client-side via HTMX (`hx-get` + `hx-target`). On a
drawer open, the default tab is loaded synchronously so the user sees
content immediately.

#### 5.2.5 Drawer Footer Actions

Sticky to the bottom of the drawer. Order:

1. **Destructive actions on the LEFT** (Deactivate, Terminate) — `--color-danger`
   outline button. Always confirmation-modal-gated.
2. **Secondary actions in the CENTER** (Download, Duplicate, Copy link).
3. **Primary action on the RIGHT** (Edit Details, Approve, Reject) — filled
   `--color-primary`.

The exact set depends on the entity and tab; the rule is **at most one
destructive**, **at most one primary**, **any number of secondary**.

### 5.3 Global Command Palette (Cmd-K)

A searchable command bar invoked by `Cmd/Ctrl-K` from anywhere in the
dashboard.

| Section | Source | Behaviour |
|---------|--------|-----------|
| Quick nav | Static sidebar items | Enter to navigate |
| Employees | `/api/v1/employees/?search=…` | Enter opens the row's drawer |
| Departments | `/api/v1/departments/?search=…` | Enter opens the department view |
| Recent items | `localStorage` | Last 8 visited entities |
| Actions | Static ("Create Employee", "Approve All Pending Leave") | Permission-gated |

The palette is a centred modal (max-width 640px) with a single input,
keyboard arrow navigation, and HTMX-loaded result lists.

---

## 6. Color Palette Strategy

### 6.1 The Principle

The colour palette must feel **authoritative, professional, and clean**. We are
building for HR Admins wearing collared shirts at desks, not designers picking
swatches on Dribbble. The palette is restrained — at most three accent hues
ever visible on a single screen, plus neutral greyscale for everything else.

### 6.2 Base Palette (Reference)

This guide does not redefine the colour tokens; it relies on
[docs/ui-ux-brief.md §2](ui-ux-brief.md) as the single source of truth. The
**decision rules** below describe *when to use which token*, not the hex.

### 6.3 Token Usage Rules

| Situation | Token | Rationale |
|-----------|-------|-----------|
| Primary buttons, primary links, focused table row | `--color-primary` | Action affordance |
| Page background | `--color-bg` | Lowest layer |
| Card surface, drawer body | `--color-bg-card` | One step above page |
| Sidebar, alternate sections, table header | `--color-bg-card-2` | Visual band separation |
| Borders, dividers, table row separators | `--color-border` | Quiet structure |
| Body text | `--color-text` | Always primary data |
| Captions, labels, secondary text | `--color-text-muted` | Hierarchy without shouting |
| Timestamps, helper text | `--color-text-subtle` | Quietest layer |

### 6.4 Semantic Palette Rules

The semantic palette (`--color-success`, `--color-warning`, `--color-danger`)
is reserved for **status** and **state**. Do not use it for branding,
decoration, or arbitrary emphasis.

**Test**: every use of a semantic colour should be answerable to "what state
does this convey?" If the answer is "none, I just wanted to highlight it",
use a neutral token or `--color-primary` instead.

### 6.5 The "Three Accent" Rule

No single screen should display more than three accent hues simultaneously,
where "accent hue" means any of: `--color-primary`, `--color-accent`,
`--color-success`, `--color-warning`, `--color-danger`. A status label
("Active") on a row in a table with a focused row (primary) and a
notification toast (success) is fine — that's three. A fourth would be visual
overload.

### 6.6 Status Label Colour Map

Already defined in [docs/ui-ux-brief.md §2](ui-ux-brief.md). The **additional
guidance** for tables:

- Row backgrounds never get tinted in a status colour. Use a left-edge accent
  bar (3px, full row height) in the status colour, instead.
- Two status labels in the same row must be visually distinguishable — don't put a
  warning label directly next to a danger label without a separator.

### 6.7 Dark vs. Light

Per [docs/ui-ux-brief.md §1.2](ui-ux-brief.md), Nexus is **dark-only**. This
guide does not plan for a light mode. If a future requirement demands it,
follow the layered approach in `ui-ux-brief.md` §2 — same tokens, inverted
lightness — rather than redefining colours per surface.

---

## 7. Typography

### 7.1 Font Choice

**Primary typeface**: **Inter** (Google Fonts).

Per [docs/ui-ux-brief.md §3](ui-ux-brief.md), Inter is the canonical typeface
for Nexus — there is **no other typeface** in the system. This dashboard
guide does not introduce alternates.

Inter is the chosen font for the following reasons:

- Optimised for UI at small sizes — x-height and letterforms are tuned for
  dense data tables.
- Excellent weight range (300–800), supports tabular numerals.
- Open-source and free, served via Google Fonts CDN with predictable
  performance.
- Industry standard for SaaS dashboards — immediately recognisable to the
  target audience as "professional tool, not consumer app".

The font stack is defined once at `:root` and never overridden at the
component level. If a screen requires tabular numerals (for aligned money,
dates, or counters), use Inter's tabular-numerals OpenType feature
(`font-feature-settings: "tnum"` or `font-variant-numeric: tabular-nums`)
rather than switching fonts.

**Fallback stack**: `'Inter', system-ui, -apple-system, "Segoe UI", Roboto,
sans-serif`. System fallbacks keep the UI usable in offline scenarios.

### 7.2 Type Scale for Data Screens

The scale in [docs/ui-ux-brief.md §3](ui-ux-brief.md) is the system. The
**data-screen-specific additions**:

| Role | Size | Weight | Notes |
|------|------|--------|-------|
| Table row primary | 14px | 500 | Names, identifiers |
| Table row secondary | 13px | 400 | Sub-text in same cell |
| Table header | 12px | 600 | Uppercase, 0.05em letter-spacing |
| Status label | 11px | 600 | Uppercase, 0.04em |
| Tabular numerals | inherit | inherit | `font-variant-numeric: tabular-nums` on all money, dates, counters |
| Drawer title | 20px | 700 | Employee full name |
| Drawer subtitle | 13px | 400 | emp_number · position |

### 7.3 Numeric Alignment

All numeric columns (money, dates, counts) must:

1. Use `font-variant-numeric: tabular-nums` so digits align across rows.
2. Be right-aligned in tables.
3. Locale-format per the tenant's language (default `id-ID` → `Rp 10.000.000`,
   dates `15 Mar 2024`).

---

## 8. Component Catalog

A flat, readable inventory. Each component references which screens it
appears in and which design tokens it depends on. No pixel values — those
live in `ui-ux-brief.md`.

### 8.1 Table — Site Roster (Primary Surface)

**Endpoint**: `GET /api/v1/employees/?status=&department_id=&is_active=`
**Permission**: Authenticated (read), HR Admin (write)
**Source**: [apps/apis/v1/employees/views.py](../apps/apis/v1/employees/views.py) → `EmployeeViewSet.list`

| Column | Source field | Notes |
|--------|--------------|-------|
| Checkbox | — | Bulk-select |
| Emp # | `emp_number` | Monospace numerals, 13px |
| Name | `first_name + last_name` | Avatar + name + email subline |
| Department | `department_name` (from `department.name`) | Link to department view (V2) |
| Position | `position_title` | Muted text |
| Status | `status` | Label — Active/Inactive/Resigned/Terminated |
| Employment | `employment_type` | Label — Permanent/Contract/Probation/Part-time/Intern |
| Joined | `join_date` | ISO short |
| Base Salary | `base_salary` | Locale-formatted, HR Admin only |
| Actions | — | Trailing ⋯ menu |

**Density toggle**: standard by default; admins can flip to compact for
triage mode or comfortable for review mode (§5.1.1).

**Toolbar features**:
- Search box (debounced 200ms, server-side via `?search=`)
- Department filter (cascading dropdown from `/api/v1/departments/`)
- Status filter (multi-select chips)
- Employment type filter
- Bulk actions: Export CSV, Deactivate selected (HR Admin only)
- Column visibility menu (§5.1.3)

### 8.2 Drawer — Employee Profile

**Endpoint**: `GET /api/v1/employees/{id}/`
**Permission**: Owner or HR Admin
**Source**: [apps/apis/v1/employees/views.py](../apps/apis/v1/employees/views.py) → `EmployeeViewSet.retrieve`

| Tab | Endpoint | Notes |
|-----|----------|-------|
| Profile | `GET /api/v1/employees/{id}/` | Identity, employment, salary, manager chain |
| Documents | `GET /api/v1/employees/{id}/documents/` | All `EmployeeDocument` rows; upload control |
| Shifts | (Attendance) `GET /api/v1/employees/{id}/shifts/today/` | Conditional on module flag |
| Leave | (Attendance) `GET /api/v1/employees/{id}/leave/balance/` | Conditional on module flag |
| HSE | (HSE) `GET /api/v1/employees/{id}/inductions/` | Conditional on module flag |
| Payroll | (Payroll) `GET /api/v1/employees/{id}/payslips/?limit=6` | Conditional on module flag |

**Profile tab cards** (in order):
1. **Identity Card** — name, emp_number, photo (or initials avatar), email,
   mobile phone, gender, DOB, place of birth.
2. **Employment Card** — department, position, level, manager, join date,
   employment type, status label.
3. **Salary Card** (HR Admin only) — base salary, salary band
   (`Position.base_salary_min`–`max`), last updated.
4. **Address Card** — residential address, ID-card address.
5. **Documents Card** — embedded list, "View all →" jumps to Documents tab.
6. **Activity Card** — last 5 audit events from
   `apps/audit/models.py`.

### 8.3 Drawer — Document Detail

**Endpoint**: `GET /api/v1/employees/{employee_pk}/documents/{id}/`
**Source**: [apps/apis/v1/documents/views.py](../apps/apis/v1/documents/views.py)

Renders inside the Documents tab of the Employee drawer. Shows:

- Document type (`doc_type`) label (KTP, NPWP, Contract, Ijazah, SIM,
  Sertifikat, Other)
- File name + size + MIME type
- Upload date (`created_at`) and uploader
- Expiry date (`valid_until`) — with a coloured countdown: green > 30 days,
  amber ≤ 30 days, red ≤ 7 days or expired
- Verified status label
- Signed URL preview link — never expose raw `file_url`
- Actions: Download (signed URL), Verify / Unverify (HR Admin), Delete (HR
  Admin, soft)

### 8.4 Form — New Employee

**Endpoint**: `POST /api/v1/employees/`
**Source**: [apps/employees/schemas.py](../apps/employees/schemas.py) → `EmployeeCreateSchema`

A multi-step wizard rendered as a full page (not a drawer) because it's a
multi-field write flow that benefits from focus.

Step pattern:

1. **Identity** — first/last name, email, mobile phone
2. **Personal** — gender, DOB, place of birth, ID-card address, residential
   address
3. **Employment** — department, position, employment type, join date,
   direct manager, status
4. **Compensation** (HR Admin only) — base salary
5. **Account** — optional: create AuthUser for self-service login
6. **Review** — read-only summary, submit

Each step is a separate URL (`/employees/new/step/1/`, `/step/2/`, etc.) with
HTMX-driven navigation. Server validates each step's payload before advancing.

### 8.5 Empty States

Empty states for tables are **never** illustrated. They are:

- A short, sentence-case headline (e.g. "No employees yet").
- One sentence of explanation (e.g. "Add your first employee to start
  tracking master data.").
- A primary CTA button matching the page's primary action.

Visual treatment: centred in the empty table area, with `--color-text-muted`
copy and the standard primary button.

### 8.6 Loading States

- **First paint**: server-rendered HTML (no skeletons). The table renders with
  a thin top progress bar (`--color-primary`, 2px, indeterminate animation)
  while data loads.
- **Partial update (HTMX)**: the affected region shows a subtle shimmer — a
  1px gradient sweep across the row, `--color-text-subtle` at 30% opacity.
- **Full page load**: a centred spinner with the company logo, 200ms fade-in.

Never use skeleton screens for tables — they cause content shift on every
reload and break the "scanning" mental model.

### 8.7 Error States

- **Inline form errors** under the relevant field, in `--color-danger`.
- **Toast notifications** (top-right, auto-dismiss 5s) for action results:
  save success, save failure, validation error.
- **Full-page error** for catastrophic failures — neutral copy, retry button,
  contact support link. Never a stack trace.

### 8.8 Modal Dialogs

Used sparingly. Reserved for:

- Destructive confirmations ("Deactivate this employee? This cannot be
  undone from the dashboard.")
- Multi-step sub-flows that interrupt the parent
- Upgrade prompts when an HR Admin tries to access a module-gated feature

Modal overlay: `--color-bg` at 60% opacity. Centred, max-width 480px. Esc
and overlay-click both close (with confirmation if dirty).

---

## 9. Shift-Aware UI

### 9.1 The Shift Model (Backend — Future)

The `apps/attendance` app is stubbed. When implemented, it will introduce
`Shift`, `ShiftAssignment`, and `AttendanceLog` models. The shift-aware UI
will:

- Default all time-scoped views (Site Roster, Live Status, etc.) to the
  **current shift** based on the company's local timezone
  (`Company.geofence_*` already exists — extend with `timezone`).
- Allow admins to switch the visible time window via a "shift picker" in the
  top bar: "Morning shift 06:00–14:00" / "Afternoon 14:00–22:00" /
  "Night 22:00–06:00" / "All hours".
- Persist the chosen window to `localStorage` so refreshes don't reset it.

### 9.2 The Top-Bar Shift Clock

A persistent indicator showing the current local time and active shift:

```
[● Morning Shift]   09:42 WIB · 4h 18m remaining
```

Click → opens a popover with:

- Shift schedule (today's three shifts with start/end)
- Current employee count per shift (live)
- Quick link to "Shift handover report"

The pulsing dot uses `--color-success`, 8px diameter, slow pulse animation
(2s cycle). Respects `prefers-reduced-motion`.

### 9.3 Live-Row Indicator

For employees currently between clock-in and clock-out, render a 3px
left-edge accent bar in `--color-success`. This is the only animation
allowed on a table row.

| Status | Edge bar |
|--------|----------|
| On shift right now | `--color-success`, 3px, no animation |
| Scheduled but not clocked in | `--color-primary`, 3px |
| Off shift | none |
| On leave | none (status label says so) |

### 9.4 Shift-Transition Banner

12 minutes before a shift change, render a dismissible banner above the
page header:

> **Shift handover in 12 minutes.** 14 employees from the morning shift
> are still clocked in. [Review] [Dismiss]

This banner is non-blocking, slide-down animation (180ms), and lives just
below the top bar.

---

## 10. Responsive Behaviour

### 10.1 Breakpoints

Inheriting from [docs/ui-ux-brief.md §10](ui-ux-brief.md):

| Name | Max-width | Behaviour |
|------|-----------|-----------|
| XL desktop | ≥ 1440px | Full sidebar, density toggle works fully |
| L desktop | 1200–1439px | Full sidebar, density toggle works fully |
| Tablet landscape | 1024–1199px | Sidebar collapses to icons by default |
| Tablet portrait | 768–1023px | Sidebar hidden behind a hamburger; tables become card-list |
| Mobile | ≤ 768px | Not a target. Render a "best on desktop" message |

### 10.2 Mobile Disclaimer

The dashboard is **not designed for mobile**. We render a small message at
viewport ≤ 768px:

> "Nexus dashboard is optimised for desktop. For field use, please open
> the Nexus mobile app."

This is intentional. Trying to make the data tables readable at 360px
would compromise the core experience. The Flutter app exists for field
workers.

### 10.3 Table Responsiveness

Below 1024px the table swaps to a **card-list layout** for that breakpoint
only:

- Each row becomes a card with stacked key-value pairs.
- Density toggle is hidden.
- Drawers open as full-screen sheets instead of side panels.

This is a graceful degradation, not a primary mode.

---

## 11. Accessibility

### 11.1 Standards

The dashboard targets **WCAG 2.1 AA**. From
[docs/ui-ux-brief.md §11](ui-ux-brief.md):

- All text ≥ 4.5:1 contrast against its background.
- Status never colour-alone.
- Focus rings always visible (`box-shadow: 0 0 0 2px var(--color-primary)`).
- `prefers-reduced-motion` disables all animations.
- Semantic HTML throughout.

### 11.2 Keyboard Navigation

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl-K` | Open command palette |
| `g` then `e` | Navigate to Employees |
| `g` then `d` | Navigate to Dashboard |
| `j` / `k` | Next / previous row |
| `Enter` on a focused row | Open drawer |
| `Esc` with drawer open | Close drawer |
| `Cmd/Ctrl-Enter` in a form | Submit form |
| `?` | Open keyboard shortcut reference |

Shortcuts are listed in a keyboard-shortcut sheet, accessible from the user
menu.

### 11.3 Screen Reader Support

- Drawer open → `aria-modal="true"`, `role="dialog"`, `aria-labelledby` points
  to the drawer title.
- Table → `<table>` with `<caption>` describing the data, `<th scope="col">`
  for headers, `aria-sort` on sortable columns.
- Status labels → `aria-label` describing the full state, e.g.
  `aria-label="Status: Active"`.
- Live regions → toast notifications use `aria-live="polite"`.

### 11.4 Color Independence

Every status colour is paired with either an icon or a text label per the
WCAG 1.4.1 rule. In the table, a "Resigned" row carries both a grey status
label **and** the text "Resigned". If the label is the only visible element,
an icon is added.

---

## 12. Implementation Conventions

### 12.1 File Layout (Planned)

```
templates/
├── base.html                     ← shell: top bar + sidebar + content slot
├── index.html                    ← marketing landing (existing)
├── partials/
│   ├── topbar.html
│   ├── sidebar.html
│   ├── page-header.html
│   ├── table-toolbar.html
│   ├── density-toggle.html
│   ├── drawer-shell.html
│   ├── shift-clock.html
│   ├── toast.html
│   ├── empty-state.html
│   └── command-palette.html
├── employees/
│   ├── list.html                 ← site roster
│   ├── detail.html               ← full page (rarely visited)
│   ├── new/
│   │   ├── step-1-identity.html
│   │   ├── step-2-personal.html
│   │   ├── step-3-employment.html
│   │   ├── step-4-compensation.html
│   │   ├── step-5-account.html
│   │   └── step-6-review.html
│   └── partials/
│       ├── row.html              ← HTMX-loaded row
│       ├── drawer-profile-tab.html
│       └── drawer-documents-tab.html
├── departments/
├── documents/
├── dashboard/
│   └── index.html
├── auth/
│   ├── login.html
│   └── password-change.html
└── errors/
    ├── 403.html
    ├── 404.html
    └── 500.html

static/
├── css/
│   ├── tokens.css                ← :root custom properties (single source)
│   ├── base.css                  ← reset + body
│   ├── shell.css                 ← top bar + sidebar
│   ├── table.css                 ← table + density modes
│   ├── drawer.css                ← slide-over drawer
│   ├── forms.css                 ← inputs, validation
│   ├── labels.css                ← status labels
│   ├── nav.css                   ← sidebar nav
│   └── responsive.css            ← media queries
└── js/
    ├── density.js                ← persistence + apply
    ├── drawer.js                 ← open/close, focus trap, URL sync
    ├── command-palette.js
    ├── htmx-helpers.js           ← CSRF, error handling
    └── keyboard.js               ← shortcuts
```

### 12.2 Naming Conventions

Inheriting from [docs/ui-ux-brief.md §14](ui-ux-brief.md):

- CSS classes: kebab-case — `.site-roster`, `.drawer-shell`,
  `.density-compact`.
- JS variables: camelCase.
- Data attributes: `data-kebab-case` — `data-row-id="..."`.
- Template files: snake_case — `employee_drawer_profile_tab.html`.
- HTMX partial fragments: suffix `_partial` — `employee_row_partial`.

### 12.3 Density Toggle Contract

The density toggle persists to `localStorage`:

```js
// key: nexus.tableDensity
// values: "compact" | "standard" | "comfortable"
// default: "standard"

// On page load:
const density = localStorage.getItem("nexus.tableDensity") || "standard";
document.documentElement.dataset.tableDensity = density;

// On toggle change:
document.documentElement.dataset.tableDensity = newMode;
localStorage.setItem("nexus.tableDensity", newMode);
```

The CSS reads `[data-table-density="compact"]` etc. to switch row
padding, font size, and avatar visibility.

### 12.4 HTMX Integration Patterns

The dashboard uses HTMX for partial updates. Conventions:

| Pattern | Implementation |
|---------|----------------|
| Initial paint | Server-rendered HTML (full page) |
| Search/filter update | `hx-get` on the search input, debounced 200ms client-side, swaps the `<tbody>` |
| Row drawer open | `hx-get` triggered by row click, target = drawer slot in `<body>` |
| Tab swap inside drawer | `hx-get` on tab click, target = drawer tab content area |
| Form submit | Standard form POST with `hx-post`, swap the form region, show toast |
| Bulk action | `hx-post` with selected row IDs in the body |

CSRF: Django's CSRF token is read once at page load and injected into every
HTMX request via `htmx:configRequest` event.

Errors: a global HTMX response handler reads the JSON error envelope and
toasts the user; for 401, redirect to login.

### 12.5 API Client Conventions

The dashboard ships a thin `nexus-api.js` wrapper around `fetch`:

```js
// All API calls return { data, error, meta } where:
// - data: parsed JSON or null
// - error: { code, message, details? } or null
// - meta: { status, headers, duration }
//
// Auth: bearer token in localStorage 'nexus.accessToken'.
//
// Pagination: list() returns { results, count, next, previous } matching the
// standard envelope.
//
// Errors: any non-2xx becomes an Error with .code = data.error.
```

This wrapper is the single source of fetch logic. Templates and HTMX
attributes never call `fetch` directly.

### 12.6 State Persistence

What goes in `localStorage`:
- `nexus.tableDensity` — table density preference
- `nexus.columns.<table>` — column visibility/order
- `nexus.sidebarCollapsed` — sidebar collapse state
- `nexus.recentItems` — last 8 visited entities (for command palette)

What does **not** go in `localStorage`:
- Auth tokens (httpOnly cookies in production; in-memory only)
- Employee data (always from the API; never cache PII in the browser)

---

## 13. Screen Inventory (Planning Index)

A flat index of every screen the dashboard ships with, organised by module.
Use this as the acceptance checklist for each component in §8.

### 13.1 Always-On (Core Module)

| # | Screen | Route | Primary surface |
|---|--------|-------|-----------------|
| 1 | Login | `/auth/login/` | Form |
| 2 | Dashboard | `/dashboard/` | Stat tiles + recent activity + pending approvals |
| 3 | Employees — List | `/employees/` | Table (§8.1) |
| 4 | Employees — Detail (full page) | `/employees/{id}/` | Tabbed view |
| 5 | Employees — Drawer | `?employee={id}` overlay | Slide-over (§8.2) |
| 6 | New Employee — Wizard | `/employees/new/step/{n}/` | Multi-step form (§8.4) |
| 7 | Departments — List | `/departments/` | Tree view + table |
| 8 | Departments — Detail | `/departments/{id}/` | Tabs (positions, employees) |
| 9 | Profile / Settings | `/me/` | Self-service |

### 13.2 Conditional (Module-Gated)

| # | Screen | Gated by | Notes |
|---|--------|----------|-------|
| 10 | Attendance — Live Status | `has_attendance` | Shift-aware roster |
| 11 | Attendance — Shifts | `has_attendance` | Shift schedule editor |
| 12 | Attendance — Leave Approvals | `has_attendance` | Approval queue |
| 13 | HSE — Violations | `has_hse` | Violation log + photos |
| 14 | HSE — Man Hours | `has_hse` | Aggregations + charts |
| 15 | HSE — Inductions | `has_hse` | Expiry matrix |
| 16 | HSE — Work Permits | `has_hse` | Permit lifecycle |
| 17 | Payroll — Runs | `has_payroll` | Run lifecycle |
| 18 | Payroll — Payslips | `has_payroll` | Per-employee payslip viewer |
| 19 | Payroll — Settings | `has_payroll` | PPh 21 brackets, BPJS rates |

Each conditional screen follows the same shell + drawer pattern but uses
entity-specific tabs and cards.

---

## 14. Open Questions / Decisions Pending

These are explicitly out of scope for *this* guide and need a separate
decision before implementation.

1. **Theme switching** — currently dark-only per `ui-ux-brief.md`. If a
   customer demands light mode, the layered approach there will be reused;
   this guide does not plan for it.
2. **Inline cell editing** — deferred to V2 (§5.1.6). Validate with usage
   data first.
3. **Internationalisation** — backend is `id-ID`; UI copy is in English for
   the dashboard. Bahasa Indonesia support is a Phase 2 item and will use
   Django's `i18n` machinery.
4. **Real-time updates** — WebSockets vs. polling for live attendance feed.
   Not decided yet; the Live-Row Indicator (§9.3) assumes WebSockets but
   can fall back to 30-second polling without UI changes.
5. **Document viewer** — preview PDFs and images inline in the drawer, or
   open in a new tab to a sandboxed viewer. Default to new-tab; revisit if
   preview usage is high.
6. **Audit log view** — currently listed in the Employee drawer Activity
   Card but a full Audit Log screen is not planned. Add when an audit
   review workflow is defined.

---

## 15. References

Internal:

- [docs/ui-ux-brief.md](ui-ux-brief.md) — design tokens, motion, responsive
- [docs/PRD-overview.md](PRD-overview.md) — product scope, personas, modules
- [docs/technical-requirement-document.md](technical-requirement-document.md) — API contracts, response envelopes, error format
- [docs/database-schema.md](database-schema.md) — entity relationships
- [apps/employees/models.py](../apps/employees/models.py) — Employee entity
- [apps/documents/models.py](../apps/documents/models.py) — EmployeeDocument entity
- [apps/departments/models.py](../apps/departments/models.py) — Department, Position
- [apps/companies/models.py](../apps/companies/models.py) — Company, SubscriptionPlan
- [apps/users/models.py](../apps/users/models.py) — AuthUser, RefreshToken
- [apps/shared/permissions.py](../apps/shared/permissions.py) — RBAC + module gates
- [apps/shared/utils/pagination.py](../apps/shared/utils/pagination.py) — NexusPaginator
- [apps/apis/v1/employees/](../apps/apis/v1/employees/) — Employee API
- [apps/apis/v1/documents/](../apps/apis/v1/documents/) — Documents API
- [apps/apis/v1/departments/](../apps/apis/v1/departments/) — Departments API
- [apps/apis/v1/auth/](../apps/apis/v1/auth/) — Authentication API
- [config/urls.py](../config/urls.py) — root URL routing
- [config/settings/base.py](../config/settings/base.py) — DRF + JWT + middleware config

External:

- WCAG 2.1 AA — https://www.w3.org/WAI/WCAG21/quickref/
- HTMX documentation — https://htmx.org/docs/
- Inter typeface — https://rsms.me/inter/

---

**Document owner**: Design (to be assigned)
**Last reviewed**: 2026-07-21
**Next review**: When the Employees List screen implementation begins
