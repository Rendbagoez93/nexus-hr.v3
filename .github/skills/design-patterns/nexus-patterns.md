# Nexus Design Patterns — Domain-Specific Guide

This guide shows how to apply design patterns **within the Nexus codebase** using real domain entities (Employee, Payroll, Attendance, HSE). It's not about memorizing pattern names — it's about recognizing when a pattern naturally fits a Nexus feature and avoiding over-engineering where Django/DRF idioms are clearer.

**Guiding principle**: Prefer explicit, boring code over clever abstractions. Use patterns to solve actual complexity, not to demonstrate pattern knowledge.

---

## 1. Patterns You're Already Using (Don't Over-Engineer)

Django and DRF naturally implement many classic patterns. Recognize them, but don't force additional abstraction layers.

| Pattern | Already Implemented As | ❌ Don't Do This |
|---------|----------------------|------------------|
| **Factory Method** | Django managers (`Employee.objects`), `factory_boy` test factories | Creating abstract factory hierarchies for simple object creation |
| **Repository** | Selectors layer (`apps/*/selectors.py`) with querysets | Adding a separate Repository class when selectors already exist |
| **Service Layer** | Services layer (`apps/*/services.py`) with business logic | Moving logic into "managers", "controllers", or "handlers" |
| **Strategy** | Pass functions as parameters to services | Creating Strategy interface hierarchies with `execute()` methods |
| **Adapter** | DRF serializers (models → JSON), third-party API clients | Adapter layers between internal Django models |
| **Observer** | Django signals (use sparingly!) | Manual Observer implementation when signals exist |
| **Template Method** | DRF ViewSet with overridden methods (`get_queryset()`, `perform_create()`) | Abstract base views with 10+ hook methods |
| **Proxy** | Django ORM lazy loading, `select_related`/`prefetch_related` | Manual proxy wrappers around models |
| **Decorator** | Python `@decorator` syntax, DRF `@action` | Chaining 5+ decorators for permissions/logging |

### Example: Factory Method (Already Natural in Django)

```python
# ✅ GOOD — Django manager is already a Factory Method
employees = Employee.objects.for_company(company_id).filter(status="active")

# ❌ BAD — Don't wrap in an abstract factory
class EmployeeFactory(ABC):
    @abstractmethod
    def create_employee(self) -> Employee:
        pass

class ActiveEmployeeFactory(EmployeeFactory):
    def create_employee(self) -> Employee:
        return Employee.objects.create(status="active")
```

---

## 2. When Patterns Actually Help in Nexus

### 2.1 Strategy Pattern — PPh 21 Calculation Methods

**Use when**: Multiple algorithms for the same task, chosen at runtime (monthly TER vs. annual progressive).

```python
# apps/payroll/services/pph21_calculator.py
from decimal import Decimal
from typing import Literal
from apps.payroll.models import Employee, PPh21TerRate

PPh21Strategy = Literal["ter", "progressive_annual"]

def calculate_pph21(
    *,
    employee: Employee,
    monthly_gross: Decimal,
    strategy: PPh21Strategy = "ter"
) -> Decimal:
    """Calculate PPh 21 using different strategies.
    
    Strategy pattern: avoid if/else chains when adding new calculation methods.
    """
    calculators = {
        "ter": _calculate_ter,
        "progressive_annual": _calculate_progressive_annual,
    }
    
    if strategy not in calculators:
        raise ValueError(f"Unknown PPh 21 strategy: {strategy}")
    
    return calculators[strategy](employee, monthly_gross)


def _calculate_ter(employee: Employee, monthly_gross: Decimal) -> Decimal:
    """TER (Tarif Efektif Rata-rata) — monthly withholding via lookup table.
    
    PMK 168/2023 method for permanent employees.
    """
    ter_category = employee.get_ter_category()  # A, B, or C
    rate = PPh21TerRate.objects.get_rate_for(
        category=ter_category,
        monthly_income=monthly_gross
    )
    return monthly_gross * rate


def _calculate_progressive_annual(employee: Employee, monthly_gross: Decimal) -> Decimal:
    """Annual reconciliation using progressive Article 17 rates.
    
    Used in December or final month to reconcile full-year liability.
    UU HPP 7/2021: 5%, 15%, 25%, 30%, 35% across income bands.
    """
    annual_taxable = employee.get_annual_taxable_income()
    # Apply progressive brackets (implementation details omitted)
    annual_tax = _apply_progressive_brackets(annual_taxable)
    prior_withheld = employee.get_ytd_withheld_pph21()
    return annual_tax - prior_withheld
```

**Why this works**: Adding a new calculation method (e.g., `"non_employee_freelance"`) requires zero changes to existing code — just add a new function to the `calculators` dict.

---

### 2.2 Chain of Responsibility — Attendance Validation

**Use when**: Multiple validators, each checking one thing, short-circuit on first failure.

```python
# apps/attendance/services/clock_in_validators.py
from typing import Protocol
from django.core.exceptions import PermissionDenied
from apps.attendance.exceptions import OutsideGeofenceError, InductionExpiredError
from apps.attendance.models import Employee

class ClockInValidator(Protocol):
    """Validator interface — each validator checks exactly one rule."""
    
    def validate(
        self,
        *,
        employee: Employee,
        latitude: float,
        longitude: float,
        client_type: str
    ) -> None:
        """Raise an exception if validation fails."""
        ...


class MobileClientValidator:
    """Enforce mobile-only clock-in at the service layer."""
    
    def validate(self, *, employee: Employee, latitude: float, longitude: float, client_type: str) -> None:
        if client_type != "flutter-mobile":
            raise PermissionDenied("Clock-in is mobile-only for all users.")


class GeofenceValidator:
    """Check employee is within company's allowed radius."""
    
    def validate(self, *, employee: Employee, latitude: float, longitude: float, client_type: str) -> None:
        if not is_within_geofence(employee.company, latitude, longitude):
            raise OutsideGeofenceError(
                f"Location ({latitude}, {longitude}) is outside allowed radius "
                f"for {employee.company.name}."
            )


class InductionValidator:
    """Check employee has valid site induction before clocking in."""
    
    def validate(self, *, employee: Employee, latitude: float, longitude: float, client_type: str) -> None:
        if not employee.has_valid_induction():
            raise InductionExpiredError(
                f"Employee {employee.emp_number} induction has expired. "
                "Renew before clocking in."
            )


class ShiftAssignmentValidator:
    """Check employee has an active shift assignment for today."""
    
    def validate(self, *, employee: Employee, latitude: float, longitude: float, client_type: str) -> None:
        from apps.attendance.selectors import employee_has_shift_today
        
        if not employee_has_shift_today(employee):
            raise ValueError(f"No shift assigned for {employee.emp_number} today.")


def clock_in(
    *,
    employee: Employee,
    latitude: float,
    longitude: float,
    photo: UploadedFile,
    client_type: str
) -> AttendanceRecord:
    """Clock in with validation chain.
    
    Each validator checks one rule. First failure stops the chain.
    Adding new checks (e.g., license validity) requires zero changes to existing validators.
    """
    validators: list[ClockInValidator] = [
        MobileClientValidator(),
        GeofenceValidator(),
        InductionValidator(),
        ShiftAssignmentValidator(),
    ]
    
    for validator in validators:
        validator.validate(
            employee=employee,
            latitude=latitude,
            longitude=longitude,
            client_type=client_type
        )
    
    # All validations passed — create record
    return AttendanceRecord.objects.create(
        employee=employee,
        clock_in_time=get_current_utc_datetime(),
        clock_in_latitude=latitude,
        clock_in_longitude=longitude,
        clock_in_photo=photo,
        company=employee.company,
    )
```

**Why this works**: Each validator is independent, testable in isolation, and new validators don't break existing ones. The chain reads like English: "validate mobile, then geofence, then induction, then shift."

---

### 2.3 Builder Pattern — PayrollRun Construction

**Use when**: Complex object requires many optional steps before finalization.

```python
# apps/payroll/services/payroll_builder.py
from decimal import Decimal
from datetime import date
import uuid
from django.db import transaction
from apps.payroll.models import PayrollRun, Payslip, Employee
from apps.shared.utils.dates import get_current_utc_datetime

class PayrollRunBuilder:
    """Builder for complex payroll run with optional components.
    
    Fluent interface makes construction readable:
    
        payroll = (
            PayrollRunBuilder(company_id, period)
            .for_employees(employee_ids)
            .with_overtime(True)
            .with_backpay(adjustments)
            .build()
        )
    """
    
    def __init__(self, company_id: uuid.UUID, period: date):
        self.company_id = company_id
        self.period = period
        self.employee_ids: list[uuid.UUID] = []
        self.include_overtime = True
        self.include_backpay = False
        self.backpay_adjustments: dict[uuid.UUID, Decimal] = {}
        self.override_rates: dict[str, Decimal] = {}
    
    def for_employees(self, employee_ids: list[uuid.UUID]) -> "PayrollRunBuilder":
        """Specify which employees to include (default: all active)."""
        self.employee_ids = employee_ids
        return self
    
    def for_all_active(self) -> "PayrollRunBuilder":
        """Include all active employees for the company."""
        self.employee_ids = list(
            Employee.objects.for_company(self.company_id)
            .filter(status="active")
            .values_list("id", flat=True)
        )
        return self
    
    def with_overtime(self, include: bool = True) -> "PayrollRunBuilder":
        """Include overtime hours in gross pay calculation."""
        self.include_overtime = include
        return self
    
    def with_backpay(self, adjustments: dict[uuid.UUID, Decimal]) -> "PayrollRunBuilder":
        """Include one-time backpay adjustments for specific employees."""
        self.include_backpay = True
        self.backpay_adjustments = adjustments
        return self
    
    def override_bpjs_rate(self, program: str, rate: Decimal) -> "PayrollRunBuilder":
        """Override BPJS rate for this payroll run only (e.g., regulation change mid-month)."""
        self.override_rates[program] = rate
        return self
    
    @transaction.atomic
    def build(self) -> PayrollRun:
        """Execute the payroll run and generate payslips.
        
        This method is idempotent — calling it twice for the same (company, period)
        will raise an error unless explicitly allowing reprocessing.
        """
        # Check for existing run
        existing = PayrollRun.objects.filter(
            company_id=self.company_id,
            period=self.period,
        ).first()
        
        if existing and existing.status in ["processing", "completed"]:
            raise ValueError(
                f"Payroll already exists for {self.company_id} / {self.period}. "
                "Use reprocess() to regenerate."
            )
        
        # Create the run
        payroll_run = PayrollRun.objects.create(
            company_id=self.company_id,
            period=self.period,
            status="processing",
            processed_at=get_current_utc_datetime(),
        )
        
        employees = Employee.objects.for_company(self.company_id).filter(
            id__in=self.employee_ids or [],
            status="active"
        )
        
        for employee in employees:
            gross_pay = self._calculate_gross(employee)
            pph21 = calculate_pph21(employee=employee, monthly_gross=gross_pay)
            bpjs_total = self._calculate_bpjs(employee, gross_pay)
            
            net_pay = gross_pay - pph21 - bpjs_total
            
            Payslip.objects.create(
                payroll_run=payroll_run,
                employee=employee,
                period=self.period,
                gross_pay=gross_pay,
                pph21_withheld=pph21,
                bpjs_employee_total=bpjs_total,
                net_pay=net_pay,
                company=employee.company,
            )
        
        payroll_run.status = "completed"
        payroll_run.save(update_fields=["status"])
        return payroll_run
    
    def _calculate_gross(self, employee: Employee) -> Decimal:
        """Calculate gross pay = base + allowances + overtime."""
        gross = employee.base_salary + employee.get_monthly_allowances()
        
        if self.include_overtime:
            gross += employee.get_overtime_pay(self.period)
        
        if self.include_backpay and employee.id in self.backpay_adjustments:
            gross += self.backpay_adjustments[employee.id]
        
        return gross
    
    def _calculate_bpjs(self, employee: Employee, gross_pay: Decimal) -> Decimal:
        """Calculate total BPJS employee contributions."""
        if self.override_rates:
            # Use override rates if provided
            return calculate_bpjs_with_overrides(employee, gross_pay, self.override_rates)
        
        return calculate_bpjs(employee=employee, monthly_gross=gross_pay)


# Usage examples

# Example 1: Standard monthly payroll for all active employees
payroll = (
    PayrollRunBuilder(company_id, date(2026, 7, 1))
    .for_all_active()
    .with_overtime(True)
    .build()
)

# Example 2: Payroll with backpay adjustments for specific employees
backpay_adjustments = {
    employee_a_id: Decimal("500000"),  # Rp 500k backpay
    employee_b_id: Decimal("1200000"),  # Rp 1.2M backpay
}

payroll = (
    PayrollRunBuilder(company_id, date(2026, 7, 1))
    .for_all_active()
    .with_overtime(True)
    .with_backpay(backpay_adjustments)
    .build()
)

# Example 3: Override BPJS rate mid-month due to regulation change
payroll = (
    PayrollRunBuilder(company_id, date(2026, 7, 1))
    .for_all_active()
    .override_bpjs_rate("kesehatan_employee", Decimal("0.01"))  # 1% → new rate
    .build()
)
```

**Why this works**: Fluent interface makes complex construction readable. Adding new options (e.g., `.with_bonus()`) doesn't break existing code. Each method returns `self`, so they chain naturally.

---

### 2.4 Adapter Pattern — External API Integration Only

**Use when**: Integrating third-party services with incompatible interfaces (BPJS API, payment gateways).

```python
# apps/payroll/adapters/bpjs_api_adapter.py
from typing import Protocol
from decimal import Decimal
import requests
from apps.payroll.models import Employee

class BPJSContributionProvider(Protocol):
    """Interface for BPJS contribution calculation."""
    
    def get_employee_contribution(self, employee: Employee, gross: Decimal) -> Decimal:
        ...


class LocalBPJSCalculator:
    """Local calculation using database rates (default)."""
    
    def get_employee_contribution(self, employee: Employee, gross: Decimal) -> Decimal:
        from apps.payroll.services.bpjs import calculate_bpjs
        return calculate_bpjs(employee=employee, monthly_gross=gross)


class BPJSAPIAdapter:
    """Adapter for official BPJS Ketenagakerjaan API.
    
    Use this when regulation requires real-time API validation instead of local calculation.
    """
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
    
    def get_employee_contribution(self, employee: Employee, gross: Decimal) -> Decimal:
        """Query BPJS API and adapt response to our Decimal format."""
        response = requests.post(
            f"{self.base_url}/contributions/calculate",
            json={
                "nip": employee.bpjs_number,
                "gross_salary": float(gross),  # API expects float
                "programs": ["kesehatan", "jht", "jp"],
            },
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10,
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Adapt API response to our domain
        total = Decimal("0")
        for program in data["contributions"]:
            total += Decimal(str(program["employee_amount"]))
        
        return total


# Usage: swap providers without changing payroll service
def calculate_payroll(employee: Employee, provider: BPJSContributionProvider):
    gross = employee.base_salary
    bpjs = provider.get_employee_contribution(employee, gross)
    return gross - bpjs

# Local calculation (default)
net = calculate_payroll(employee, LocalBPJSCalculator())

# API calculation (when required)
net = calculate_payroll(employee, BPJSAPIAdapter(api_key, base_url))
```

**When NOT to use**: Don't create adapters between internal Django models — DRF serializers already handle that.

---

## 3. Anti-Patterns to Avoid in Nexus

### ❌ 3.1 Don't: Singleton for Shared State

**Bad**: Singleton for TenantManager breaks tenant isolation.

```python
# ❌ BAD — Shared state across requests = data leak
class TenantManager:
    _instance = None
    _current_company_id = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def set_company(self, company_id):
        self._current_company_id = company_id  # DANGER: shared across requests!
```

**Good**: Each queryset gets its own manager instance.

```python
# ✅ GOOD — Stateless manager method
class TenantManager(models.Manager):
    def for_company(self, company_id: uuid.UUID):
        return self.filter(company_id=company_id)

# Every model gets its own manager instance
Employee.objects.for_company(request.company_id)
```

---

### ❌ 3.2 Don't: Abstract Factory for Employee Types

**Bad**: Creating subclasses for employment status.

```python
# ❌ BAD — Over-engineering with inheritance
class EmployeeFactory(ABC):
    @abstractmethod
    def create_employee(self) -> Employee:
        pass

class ActiveEmployeeFactory(EmployeeFactory):
    def create_employee(self) -> Employee:
        return ActiveEmployee(status="active")

class InactiveEmployeeFactory(EmployeeFactory):
    def create_employee(self) -> Employee:
        return InactiveEmployee(status="inactive")
```

**Good**: Single `Employee` model with a `status` field.

```python
# ✅ GOOD — Django model with choices
class Employee(TenantModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        RESIGNED = "resigned", "Resigned"
        TERMINATED = "terminated", "Terminated"
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

# Simple manager method
def get_active_employees(company_id: uuid.UUID):
    return Employee.objects.for_company(company_id).filter(status=Employee.Status.ACTIVE)
```

---

### ❌ 3.3 Don't: Decorator Chains for Permissions

**Bad**: Stacking 5+ decorators for every view.

```python
# ❌ BAD — Hard to read, bypasses DRF's permission system
@require_http_methods(["POST"])
@login_required
@check_company_subscription("payroll")
@check_role(["hr_admin"])
@log_action("payroll.run")
def process_payroll(request):
    ...
```

**Good**: Use DRF's declarative permission classes.

```python
# ✅ GOOD — Declarative, testable, composable
class ProcessPayrollView(APIView):
    permission_classes = [IsAuthenticated, IsHRAdmin, HasPayrollModule]
    
    def post(self, request):
        # Permission checks already ran — focus on business logic
        ...
```

---

### ❌ 3.4 Don't: Observer for Core Business Logic

**Bad**: Using signals for critical state transitions.

```python
# ❌ BAD — Hidden behavior, hard to test, order-dependent
@receiver(post_save, sender=LeaveRequest)
def auto_deduct_balance(sender, instance, created, **kwargs):
    if instance.status == "approved":
        # This runs implicitly — hard to find, hard to test
        deduct_leave_balance(instance.employee, instance.days)
```

**Good**: Explicit service call in the approval function.

```python
# ✅ GOOD — Explicit, testable, obvious
def approve_leave_request(*, leave_request: LeaveRequest, approver: Employee) -> LeaveRequest:
    """Approve leave and deduct balance."""
    leave_request.status = LeaveRequest.Status.APPROVED
    leave_request.approved_by = approver
    leave_request.save(update_fields=["status", "approved_by"])
    
    # Explicit balance deduction — no surprises
    deduct_leave_balance(employee=leave_request.employee, days=leave_request.days)
    
    return leave_request
```

**When signals ARE appropriate**: Logging, cache invalidation, analytics — decoupled concerns that don't affect correctness.

---

### ❌ 3.5 Don't: Command Pattern for Simple Actions

**Bad**: Wrapping every service function in a Command class.

```python
# ❌ BAD — Over-engineering a simple function call
class ApproveLeaveCommand:
    def __init__(self, leave_request_id: uuid.UUID, approver_id: uuid.UUID):
        self.leave_request_id = leave_request_id
        self.approver_id = approver_id
    
    def execute(self) -> LeaveRequest:
        leave_request = LeaveRequest.objects.get(id=self.leave_request_id)
        approver = Employee.objects.get(id=self.approver_id)
        # ... approval logic
        return leave_request

# Usage is more verbose than a direct function call
command = ApproveLeaveCommand(leave_id, approver_id)
result = command.execute()
```

**Good**: Just call the service function.

```python
# ✅ GOOD — Simple function call
leave_request = approve_leave_request(leave_request=leave_request, approver=approver)
```

**When Command IS appropriate**: Undo/redo functionality, queuing actions (Celery tasks), macro recording — scenarios where you genuinely need to reify actions as objects.

---

## 4. Pattern Decision Tree for Nexus

Use this to decide whether a pattern applies:

```
Is this a Django/DRF built-in concern?
├─ YES → Use the framework's idiom (managers, serializers, viewsets)
└─ NO  → Continue

Do you have 3+ interchangeable algorithms?
├─ YES → Strategy pattern (PPh 21 methods, payment gateways)
└─ NO  → Continue

Do you need multiple validators to run in sequence?
├─ YES → Chain of Responsibility (clock-in validation)
└─ NO  → Continue

Is construction complex with many optional steps?
├─ YES → Builder pattern (PayrollRun, reporting)
└─ NO  → Continue

Are you integrating an external API with incompatible interface?
├─ YES → Adapter pattern (BPJS API, payment gateway)
└─ NO  → Continue

None of the above?
└─ Write a plain service function — simpler is better
```

---

## 5. Testing Patterns in Nexus

### Pattern: Test Fixture Factory

Use `factory_boy` for complex test data (this IS the Factory pattern).

```python
# tests/factories.py
import factory
from apps.companies.models import Company
from apps.payroll.models import Payslip

class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company
    
    name = factory.Sequence(lambda n: f"Company {n}")
    industry = "manufacturing"

class EmployeeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Employee
    
    company = factory.SubFactory(CompanyFactory)
    emp_number = factory.Sequence(lambda n: f"NXS-{n:04d}")
    first_name = factory.Faker("first_name")
    email = factory.LazyAttribute(lambda obj: f"{obj.first_name.lower()}@example.com")
    base_salary = Decimal("5000000")
    status = Employee.Status.ACTIVE

# Usage in tests
def test_payroll_calculation():
    employee = EmployeeFactory(base_salary=Decimal("8000000"))
    payslip = calculate_payroll(employee)
    assert payslip.gross_pay == Decimal("8000000")
```

---

## 6. Summary

| ✅ Use | ❌ Avoid |
|--------|----------|
| Django managers (Factory Method) | Abstract factory hierarchies |
| Selectors layer (Repository) | Separate Repository classes |
| Services layer (Service pattern) | "Controllers" or "Handlers" |
| Pass functions (Strategy) | Strategy interface hierarchies |
| DRF serializers (Adapter) | Adapters between internal models |
| DRF permission classes | Decorator chains for permissions |
| Explicit service calls | Django signals for business logic |
| Plain functions | Command objects for simple actions |
| Single model with `status` field | Inheritance for entity types |

**Golden rule**: If Django or DRF already provides an idiom for your problem, use it. Only reach for a pattern when you have genuine complexity that Django doesn't address.

---

## References

- Generic design patterns: `.claude/skills/design-patterns/references/`
- Nexus architecture: `.claude/CLAUDE.md`
- Domain rules: `.claude/skills/SKILL.md` (nexus-domain)
