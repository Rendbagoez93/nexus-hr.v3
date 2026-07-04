---
name: design-patterns
description: Guide software architecture decisions by recommending appropriate design patterns for project planning. Use when the user mentions any of the following: design patterns, refactoring, architecture planning, selecting patterns for a project, "what pattern should I use", implementing a specific pattern (Factory, Singleton, Observer, Strategy, etc.), code structure decisions, or when designing class/object relationships. Also triggered by creational patterns, structural patterns, behavioral patterns, or GoF patterns.
---

# Design Patterns

Help users select and implement the right design pattern for their software architecture needs.

## Quick Decision Guide

### When User Needs to CHOOSE a Pattern

Ask these questions to narrow down:
1. **What problem are you solving?** (object creation, object composition, communication between objects, behavior variation)
2. **At what level?** (class-level or object-level)
3. **What constraints?** (flexibility, performance, simplicity)

### When User Names a Specific Pattern

Jump to implementation guidance. See references for detailed patterns:
- [Creational Patterns](references/creational.md) — Object creation mechanisms
- [Structural Patterns](references/structural.md) — Object composition and relationships
- [Structural Patterns](references/behavioral.md) — Object collaboration and communication

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

### nexus-hr-Specific Scenarios

| nexus-hr Scenario | Recommended Pattern | Where |
|-----------------|---------------------|-------|
| Creating payslip calculators that differ per industry (manufacturing, mining, office) | Factory Method | `core/payroll/services.py` |
| Clock-in validation: geofence → induction check → shift window → create record | Chain of Responsibility | `core/attendance/services.py` |
| Work permit multi-step approval engine (draft → pending → approved/rejected) | State | `core/hse/services.py` — `advance_permit_workflow` |
| Leave request lifecycle (pending → approved/rejected/cancelled) | State | `core/leave/services.py` |
| Sending notifications via FCM, email, or in-app — same interface, different delivery | Strategy | `core/notifications/services.py` |
| `AttendanceRecord` changes triggering man-hours recalculation in HSE | Observer | Celery signal → `core/hse/tasks.py` |
| Wrapping ORM QuerySet + service calls behind a clean service API | Facade | All `services.py` files |
| `CompanyQuerySet.for_company()` chaining additional filters | Decorator | `shared/querysets.py` |
| Building complex `EmployeeCreateIn` / `PayslipOut` Pydantic schemas with optional fields | Builder | `core/*/schemas.py` |
| Riverpod `AsyncNotifier` managing attendance state on mobile | Observer + State | Flutter `features/attendance/providers/` |

## Anti-Patterns to Avoid

- **Singleton abuse** — Overuse makes code hard to test, hides dependencies
- **Factory overuse** — Simple instantiation doesn't need pattern
- **Pattern obsession** — Don't force a pattern where simple code works
- **Premature abstraction** — Start simple, refactor to pattern when pain appears

## Usage Patterns

**User says:** "I'm building a game and need different enemy types"
→ Factory Method or Abstract Factory

**User says:** "My notification system needs to support multiple channels"
→ Observer pattern

**User says:** "I want to switch between payment methods easily"
→ Strategy pattern

**User says:** "How do I simplify my complex API client?"
→ Facade pattern

### nexus-hr Usage Examples

**User says:** "How do I structure the clock-in validation so each check is independent?"
→ Chain of Responsibility — each validator (geofence, induction, shift timing) is a discrete handler

**User says:** "How do I model the work permit approval workflow?"
→ State pattern — `WorkPermit.status` drives behavior; `advance_permit_workflow` is the state transition function

**User says:** "I want to send notifications via push, email, or in-app without changing the caller"
→ Strategy pattern — `NotificationChannel` interface with `FcmChannel`, `EmailChannel`, `InAppChannel` implementations

**User says:** "How should payslip generation differ between manufacturing and office employees?"
→ Factory Method — `PayslipCalculatorFactory.for_industry(industry)` returns the right calculator class

**User says:** "How do I keep service functions clean when they call ORM, cache, and external APIs?"
→ Facade pattern — the `services.py` function is the facade; callers never touch QuerySets or raw HTTP directly

## Implementation Reference

For detailed pattern information including:
- Intent and applicability
- Multi-language code examples (Python, Dart, TypeScript)
- Common pitfalls

See:
- [Pattern Quick Reference](references/pattern-reference.md) — One-page lookup table
- [AI Pseudocode Format](references/ai-pseudocode.md) — Compact, language-agnostic syntax optimized for AI
- [Creational Patterns](references/creational.md) — Object creation patterns
- [Structural Patterns](references/structural.md) — Object composition patterns
- [Behavioral Patterns](references/behavioral.md) — Object communication patterns

## Code Examples Available In

All patterns include examples in:
- � **Python** — Primary language (Django backend, services, models)
- 🎯 **Dart** — Flutter mobile app (Riverpod providers, use cases, repositories)
- 🟦 **TypeScript** — Reference only (not used in Nexus stack)
- 📝 **AI Pseudocode** — Language-agnostic, token-efficient

> When generating Nexus pattern examples, prefer **Python** for backend patterns and **Dart** for Flutter/mobile patterns.
