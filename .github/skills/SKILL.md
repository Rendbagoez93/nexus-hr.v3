---
name: design-patterns
description: Guide software architecture decisions by recommending appropriate design patterns for project planning. Use when the user mentions any of the following: design patterns, refactoring, architecture planning, selecting patterns for a project, "what pattern should I use", implementing a specific pattern (Factory, Singleton, Observer, Strategy, etc.), code structure decisions, or when designing class/object relationships. Also triggered by creational patterns, structural patterns, behavioral patterns, or GoF patterns.
---

# Design Patterns

Help users select and implement the right design pattern for their software architecture needs.

For Nexus-specific guidance — which patterns actually help in this codebase, with
real file paths and worked code — see [`design-patterns/nexus-patterns.md`](design-patterns/nexus-patterns.md).
This file stays generic; `nexus-patterns.md` is the source of truth for anything
Nexus-domain-specific below.

## Quick Decision Guide

### When User Needs to CHOOSE a Pattern

Ask these questions to narrow down:
1. **What problem are you solving?** (object creation, object composition, communication between objects, behavior variation)
2. **At what level?** (class-level or object-level)
3. **What constraints?** (flexibility, performance, simplicity)

### When User Names a Specific Pattern

Jump to implementation guidance. For concrete, Nexus-grounded examples see
[`design-patterns/nexus-patterns.md`](design-patterns/nexus-patterns.md):
- §1 — Patterns Django/DRF already implement (don't reinvent them)
- §2 — Patterns that genuinely help (Strategy, Chain of Responsibility, Builder, Adapter)
- §3 — Nexus-specific anti-patterns to avoid
- §4 — Pattern decision tree

## Pattern Categories Overview

| Category | Purpose | Common Patterns |
|----------|---------|-----------------|
| **Creational** | Instantiate objects flexibly | Factory, Builder, Singleton, Prototype |
| **Structural** | Compose objects into structures | Adapter, Decorator, Facade, Proxy, Composite |
| **Behavioral** | Manage object communication | Observer, Strategy, Command, State, Iterator |

## Common Scenarios → Pattern Mapping

| Scenario | Recommended Pattern | Why |
|----------|---------------------|-----|
| "Create objects without exposing creation logic" | Factory Method/Abstract Factory | Encapsulates instantiation |
| "Only one instance allowed" | Singleton | Controlled access to sole instance |
| "Step-by-step construction of complex objects" | Builder | Separates construction from representation |
| "Add responsibilities to objects dynamically" | Decorator | Flexible alternative to subclassing |
| "Simplify a complex subsystem" | Facade | Unified interface to complex components |
| "Objects need to be notified of changes" | Observer | Publish-subscribe dependency |
| "Vary algorithm at runtime" | Strategy | Encapsulates interchangeable algorithms |
| "Object behavior changes based on state" | State | State-specific behavior delegation |
| "Handle request without knowing exact handler" | Chain of Responsibility | Decouples sender from receiver |
| "Execute operations without coupling to request" | Command | Encapsulates request as object |

### Nexus-Specific Scenarios

> Full worked examples and code for every row below live in
> [`design-patterns/nexus-patterns.md`](design-patterns/nexus-patterns.md). Apps live
> under `apps/<module>/`, never `core/` — check the actual repo structure before
> citing a path.

| Nexus Scenario | Recommended Pattern | Where |
|---|---|---|
| Employee queries; `factory_boy` test data creation | Factory Method — already implemented, don't wrap in an abstract factory | Django managers (`Employee.objects`), `tests/factories.py` |
| Tenant-scoped read queries | Repository — already implemented as the selectors layer | `apps/*/selectors.py` |
| Business logic / mutations | Service Layer — already implemented | `apps/*/services.py` |
| PPh 21 calculation: monthly TER vs. year-end progressive reconciliation | Strategy | `apps/payroll/services/pph21_calculator.py` |
| Clock-in validation: mobile-client check → geofence → induction → shift assignment | Chain of Responsibility | `apps/attendance/services/clock_in_validators.py` |
| `PayrollRun` construction with optional overtime, backpay, rate overrides | Builder | `apps/payroll/services/payroll_builder.py` |
| Integrating the official BPJS Ketenagakerjaan API — external, incompatible interface | Adapter — external APIs only, never between internal Django models | `apps/payroll/adapters/bpjs_api_adapter.py` |
| DRF `ViewSet` hooks (`get_queryset()`, `perform_create()`) | Template Method — already implemented, don't add hook-heavy abstract base views | `apps/apis/v1/*/views.py` |
| `select_related`/`prefetch_related`, lazy FK access | Proxy — already implemented by the ORM | Django idiom, no wrapper needed |
| `@log_function_call(...)` decorator, DRF `@action` | Decorator — already implemented, don't stack 5+ custom decorators | `apps/shared/logging/logger.py`, DRF viewsets |

## Anti-Patterns to Avoid

General:
- **Factory overuse** — Simple instantiation doesn't need a pattern
- **Pattern obsession** — Don't force a pattern where simple code works
- **Premature abstraction** — Start simple, refactor to a pattern when pain appears

Nexus-specific — see `design-patterns/nexus-patterns.md` §3 for full before/after code:
- **Singleton for shared/tenant state** — breaks tenant isolation; `TenantManager` must stay stateless (`for_company(company_id)` per call, never a cached `_current_company_id`)
- **Abstract Factory / subclassing for employee status** — use one `Employee` model with a `status` `TextChoices` field, not `ActiveEmployeeFactory` / `InactiveEmployeeFactory` hierarchies
- **Decorator chains for permissions** — use DRF's declarative `permission_classes`, not 5+ stacked custom decorators
- **Signal-based Observer for core business logic** — e.g. auto-deducting leave balance in a `post_save` signal hides the transition and is hard to test; call the service function explicitly instead. Signals are fine for logging, cache invalidation, analytics — never for correctness-affecting business rules
- **Command objects for simple actions** — call the service function directly (`approve_leave_request(...)`); reserve Command for genuine undo/redo or Celery task queuing

## Usage Patterns

**User says:** "I'm building a game and need different enemy types"
→ Factory Method or Abstract Factory

**User says:** "My notification system needs to support multiple channels"
→ Observer pattern

**User says:** "I want to switch between payment methods easily"
→ Strategy pattern

**User says:** "How do I simplify my complex API client?"
→ Facade pattern

### Nexus Usage Examples

**User says:** "How do I structure the clock-in validation so each check is independent?"
→ Chain of Responsibility — each validator (mobile-client check, geofence, induction, shift assignment) is a discrete handler that raises on failure; see `nexus-patterns.md` §2.2 (`apps/attendance/services/clock_in_validators.py`)

**User says:** "How should I calculate PPh 21 when there are two different methods — monthly TER vs. year-end progressive?"
→ Strategy pattern — a `calculators` dict keyed by strategy name, not an if/else chain; see `nexus-patterns.md` §2.1 (`apps/payroll/services/pph21_calculator.py`)

**User says:** "How do I build a PayrollRun with optional overtime, backpay, and rate overrides?"
→ Builder pattern — fluent `PayrollRunBuilder(...).for_all_active().with_overtime().build()`; see `nexus-patterns.md` §2.3 (`apps/payroll/services/payroll_builder.py`)

**User says:** "How do I integrate the official BPJS API without coupling payroll logic to `requests` calls?"
→ Adapter pattern — a `BPJSContributionProvider` interface with `LocalBPJSCalculator` and `BPJSAPIAdapter` implementations, swappable at the call site; see `nexus-patterns.md` §2.4. Adapter is for external APIs only — never between internal Django models (DRF serializers already do that)

**User says:** "How do I keep service functions clean when they call ORM, cache, and external APIs?"
→ Don't add a Facade layer — the `services.py` function already is one; callers never touch QuerySets or raw HTTP directly

## Code Examples Available In

All patterns include examples in:
- � **Python** — Primary language (Django backend, services, models)
- 🎯 **Dart** — Flutter mobile app (Riverpod providers, use cases, repositories)
- 🟦 **TypeScript** — Reference only (not used in Nexus stack)
- 📝 **AI Pseudocode** — Language-agnostic, token-efficient

> When generating Nexus pattern examples, prefer **Python** for backend patterns and **Dart** for Flutter/mobile patterns.
