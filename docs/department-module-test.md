# Department Module Test Plan

**Status**: Draft
**Date**: July 2026
**Module**: `apps/departments` + `apps/apis/v1/departments`

---

## 1. Module Overview

The departments module manages two tenant-scoped models:

| Model | Purpose | Tenant Key |
|---|---|---|
| `Department` | Org units within a company; supports hierarchy via `parent` FK | `company` FK |
| `Position` | Job titles within a department; has salary band constraints | `company` FK |

Both inherit `TenantManager` (`.for_company()`) and `SoftDeleteMixin` (`is_active`, `deactivate()`, `restore()`).

---

## 2. Test Structure

Tests live in `apps/departments/tests/` and follow the Nexus three-marker convention:

| Marker | What it covers |
|---|---|
| `@pytest.mark.unit` | Service-layer functions in isolation (no DB, no HTTP) |
| `@pytest.mark.integration` | Manager + soft-delete + restore pipelines |
| `@pytest.mark.feature` | Full HTTP request/response via DRF `APIClient` |

Every write-endpoint test must include a negative-path counterpart.

---

## 3. Required Fixtures

### 3.1 Department-specific fixtures

Add to `apps/departments/tests/conftest.py` (create this file):

```python
@pytest.fixture
def department(db, company):
    """Active Department belonging to company."""
    from apps.departments.models import Department
    return Department.objects.create(
        company=company,
        name="Engineering",
        code="ENG",
    )

@pytest.fixture
def inactive_department(db, company):
    """Soft-deleted Department."""
    from apps.departments.models import Department
    dept = Department.objects.create(
        company=company,
        name="Deprecated",
        code="DEP",
    )
    dept.deactivate()
    return dept

@pytest.fixture
def two_departments(db, company):
    """Two active departments for hierarchy tests."""
    from apps.departments.models import Department
    parent = Department.objects.create(company=company, name="Operations", code="OPS")
    child = Department.objects.create(company=company, name="Maintenance", code="MNT", parent=parent)
    return parent, child

@pytest.fixture
def department_other_company(db):
    """Department owned by a second company — for cross-tenant isolation tests."""
    from apps.companies.models import Company
    from apps.departments.models import Department
    other_co = Company.objects.create(name="Other Corp", industry="office", subscription_tier="core", is_active=True)
    return Department.objects.create(company=other_co, name="Other Dept", code="OTH")
```

### 3.2 Position-specific fixtures

```python
@pytest.fixture
def position(db, company, department):
    """Active Position within department."""
    from apps.departments.models import Position
    return Position.objects.create(
        company=company,
        department=department,
        title="Software Engineer",
        level="staff",
        base_salary_min=Decimal("5000000"),
        base_salary_max=Decimal("8000000"),
    )

@pytest.fixture
def inactive_position(db, company, department):
    """Soft-deleted Position."""
    from apps.departments.models import Position
    pos = Position.objects.create(
        company=company,
        department=department,
        title="Contractor",
        level="staff",
        base_salary_min=Decimal("3000000"),
        base_salary_max=Decimal("4000000"),
    )
    pos.deactivate()
    return pos

@pytest.fixture
def position_other_company(db):
    """Position owned by a second company."""
    from apps.companies.models import Company
    from apps.departments.models import Department, Position
    other_co = Company.objects.create(name="Other Corp", industry="office", subscription_tier="core", is_active=True)
    dept = Department.objects.create(company=other_co, name="Other Dept", code="OTH")
    return Position.objects.create(
        company=other_co,
        department=dept,
        title="Other Position",
        level="staff",
        base_salary_min=Decimal("5000000"),
        base_salary_max=Decimal("8000000"),
    )
```

---

## 4. Test Cases — Department

### 4.1 Unit Tests (`test_department_service.py`)

#### Happy-path CRUD

| Test | Values | Expected Result |
|---|---|---|
| `test_create_department` | `company_id`, `name="Engineering"`, `code="ENG"`, no parent | Department created with `code="ENG"` (uppercased), `is_active=True` |
| `test_create_department_with_parent` | `company_id`, `name="Backend"`, `code="BE"`, `parent_id` of existing dept | Department created, `parent` FK set correctly |
| `test_create_department_parent_not_found` | `parent_id` pointing to non-existent dept UUID | `DepartmentError` with `detail="Parent department not found."`, `status_code=404` |
| `test_create_department_parent_wrong_company` | `parent_id` of a department in another company | `DepartmentError` 404 (enforced by `.for_company()`) |
| `test_get_by_id` | valid `pk` + matching `company_id` | Returns the `Department` instance |
| `test_get_by_id_not_found` | non-existent `pk` for company | `DepartmentError` 404 |
| `test_update_name` | `pk`, `company_id`, `name="Engineering Ops"` | Field updated, saved |
| `test_update_code` | `pk`, `company_id`, `code="en-g"` (mixed case input) | `code` saved as `"EN-G"` (uppercased via service) |
| `test_update_parent_to_null` | dept with existing parent, `parent_id=None` | `parent` FK cleared |
| `test_soft_delete` | active dept `pk` + `company_id` | `is_active=False`, `deleted_at` set |
| `test_restore` | soft-deleted dept `pk` + `company_id` | `is_active=True`, `deleted_at=None` |
| `test_restore_not_found` | non-existent or already-active dept | `DepartmentError` 404 |

#### List filtering

| Test | Values | Expected Result |
|---|---|---|
| `test_list_all_active` | `is_active=True` | Only `is_active=True` departments returned |
| `test_list_include_inactive` | `is_active=False` | Both active and inactive returned |
| `test_list_filter_by_parent` | `parent_id` of root dept | Only direct children returned |
| `test_list_empty` | company with no departments | Empty list `[]` |

---

### 4.2 Selector Tests (`test_department_selectors.py`)

| Test | Values | Expected Result |
|---|---|---|
| `test_alive_returns_only_active` | company with mix of active/inactive depts | Only `is_active=True` returned, ordered by name |
| `test_root_departments` | nested hierarchy (root + child + grandchild) | Only root (no parent) returned |
| `test_children_of` | parent dept with 2 children | Exactly 2 children returned, ordered by name |
| `test_with_children` | tree: 1 root with 2 children | Root returned with both children prefetched |

---

### 4.3 Model Tests (`test_department_models.py`)

| Test | Values | Expected Result |
|---|---|---|
| `test_str` | dept name="Engineering", code="ENG" | `"Engineering (ENG)"` |
| `test_code_uniqueness_per_company` | same `code` for two depts in same company | `IntegrityError` (DB constraint) |
| `test_code_same_across_companies_allowed` | same `code` in different companies | Both succeed (constraint is per-company) |
| `test_parent_self_reference_prevented` | dept set as its own parent | `ProtectedError` on save (PROTECT) |
| `test_deactivate_sets_deleted_at` | call `deactivate()` | `is_active=False`, `deleted_at` is a datetime, not None |
| `test_restore_clears_deleted_at` | call `restore()` on inactive dept | `is_active=True`, `deleted_at=None` |

---

### 4.4 Integration Tests (`test_department_integration.py`)

| Test | Scenario | Expected Result |
|---|---|---|
| `test_department_tree_integration` | Create 3-level hierarchy via service, query via selector | Tree root has 2 levels of children correctly nested |
| `test_create_duplicate_code_same_company` | Two creates with same code for same company | `IntegrityError` (DB-level uniqueness) |
| `test_cross_tenant_isolation` | Company A creates dept; query with Company B's `company_id` | Empty list (tenant isolation enforced) |
| `test_department_ordering` | Create 3 depts in order: Z, A, M | List returns `[A, M, Z]` ordered by name |

---

### 4.5 Feature Tests — Department API (`test_department_api.py`)

All use `hr_admin_client` (HR Admin) unless noted.

#### Happy-path

| Test | Request | Expected Result |
|---|---|---|
| `test_list_departments` | `GET /api/v1/departments/` | 200, paginated list |
| `test_list_with_parent_filter` | `GET /api/v1/departments/?parent_id=<uuid>` | 200, filtered list |
| `test_list_include_inactive` | `GET /api/v1/departments/?is_active=false` | 200, includes inactive |
| `test_create_department` | `POST /api/v1/departments/` + `{name, code}` | 201, dept in response |
| `test_create_with_parent` | `POST` + `{name, code, parent_id}` | 201, parent FK set |
| `test_retrieve_department` | `GET /api/v1/departments/{id}/` | 200, dept data |
| `test_partial_update` | `PATCH` + `{name: "New Name"}` | 200, name updated |
| `test_delete_department` | `DELETE /api/v1/departments/{id}/` | 204, soft-deleted |
| `test_restore_department` | `POST /api/v1/departments/{id}/restore/` | 200, `is_active=True` |
| `test_tree_endpoint` | `GET /api/v1/departments/tree/` | 200, nested children |

#### Negative-path (write endpoints require negative cases)

| Test | Request | Expected Result |
|---|---|---|
| `test_create_missing_name` | `POST` without `name` | 400 validation error |
| `test_create_missing_code` | `POST` without `code` | 400 validation error |
| `test_create_duplicate_code` | `POST` with existing code | 400 or 409 conflict |
| `test_create_parent_not_found` | `POST` with non-existent `parent_id` | 400/404 with "Parent department not found" |
| `test_retrieve_not_found` | `GET /api/v1/departments/{unknown-uuid}/` | 404 |
| `test_partial_update_not_found` | `PATCH` unknown UUID | 404 |
| `test_delete_not_found` | `DELETE` unknown UUID | 404 |
| `test_restore_not_found` | `POST restore/` on active or unknown UUID | 404 |
| `test_code_uppercase_normalized` | `POST` with `code="eng"` | Saved as `"ENG"` in response |

---

### 4.6 Permission Tests — Department API (`test_department_permissions.py`)

Every action × every role combination.

| Role | `list` | `retrieve` | `create` | `patch` | `delete` | `restore` | `tree` |
|---|---|---|---|---|---|---|---|
| `hr_admin` | ✅ 200 | ✅ 200 | ✅ 201 | ✅ 200 | ✅ 204 | ✅ 200 | ✅ 200 |
| `manager` | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | ✅ 200 |
| `employee` | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | ✅ 200 |
| `hse_officer` | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | ✅ 200 |
| `platform_admin` | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | ✅ 200 |
| `other_company_client` | ✅ 200 (own) | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | ✅ 200 (own) |

Cross-tenant tests: `other_company_client` accessing `company`'s department must always return **403**, never 404.

---

## 5. Test Cases — Position

### 5.1 Unit Tests (`test_position_service.py`)

#### Happy-path CRUD

| Test | Values | Expected Result |
|---|---|---|
| `test_create_position` | valid dept, `title="Engineer"`, `level="staff"`, min/max | Position created with correct fields |
| `test_create_with_salary_min_less_than_max` | `min=5_000_000`, `max=8_000_000` | Position created |
| `test_create_min_greater_than_max` | `min=10_000_000`, `max=5_000_000` | `PositionError` 400, detail contains salary message |
| `test_create_min_equals_max` | `min=5_000_000`, `max=5_000_000` | Position created (equal is allowed by DB constraint) |
| `test_create_department_not_found` | non-existent `department_id` | `PositionError` 404 |
| `test_create_department_wrong_company` | `department_id` from another company | `PositionError` 404 |
| `test_get_by_id` | valid `pk` + `company_id` | Returns `Position` instance |
| `test_get_by_id_not_found` | non-existent `pk` | `PositionError` 404 |
| `test_update_salary_range` | `base_salary_min=6_000_000`, `base_salary_max=9_000_000` | Both updated |
| `test_update_min_breaches_max` | new `base_salary_min > existing base_salary_max` | `PositionError` 400 |
| `test_update_max_breaches_min` | new `base_salary_max < existing base_salary_min` | `PositionError` 400 |
| `test_update_department` | `department_id` to a different dept | Department FK updated |
| `test_update_department_not_found` | non-existent dept ID | `PositionError` 404 |
| `test_update_department_wrong_company` | dept from another company | `PositionError` 404 |
| `test_soft_delete` | active position | `is_active=False`, `deleted_at` set |
| `test_restore` | soft-deleted position | `is_active=True`, `deleted_at=None` |
| `test_restore_not_found` | non-existent or already-active | `PositionError` 404 |

#### List filtering

| Test | Values | Expected Result |
|---|---|---|
| `test_list_all_active` | `is_active=True` | Only active positions |
| `test_list_by_department` | `department_id` filter | Only positions in that dept |
| `test_list_by_level` | `level="manager"` filter | Only manager-level positions |
| `test_list_by_department_and_level` | both filters combined | Correctly filtered |

---

### 5.2 Selector Tests (`test_position_selectors.py`)

| Test | Values | Expected Result |
|---|---|---|
| `test_alive_returns_only_active` | mix of active/inactive positions | Only active, ordered by dept then title |
| `test_for_department` | dept with 3 positions | Exactly 3 positions returned |
| `test_for_department_excludes_other_dept` | dept A and B with positions | Only dept A's positions returned |
| `test_by_level_single` | `level="manager"` | All manager positions across depts |
| `test_by_level_multiple` | `levels=["manager", "staff"]` | Both levels returned |
| `test_by_level_none` | no level filter | All active positions returned |
| `test_empty_list` | company with no positions | `[]` |

---

### 5.3 Model Tests (`test_position_models.py`)

| Test | Values | Expected Result |
|---|---|---|
| `test_str` | title="Engineer", level="staff" | `"Engineer (staff)"` |
| `test_salary_min_lte_max_constraint` | `min > max` | `IntegrityError` (DB-level check constraint) |
| `test_department_protect_on_delete` | Position in dept; try to delete dept | `ProtectedError` (PROTECT) |
| `test_deactivate` | call `deactivate()` | `is_active=False`, `deleted_at` set |
| `test_restore` | call `restore()` | `is_active=True`, `deleted_at=None` |

---

### 5.4 Integration Tests (`test_position_integration.py`)

| Test | Scenario | Expected Result |
|---|---|---|
| `test_create_duplicate_title_same_dept` | Two positions with same title in same dept | Both succeed (no uniqueness constraint on title+dept) |
| `test_position_ordering` | Create in dept order: Z, A, M | `alive()` returns `[A, M, Z]` by dept then title |
| `test_cross_tenant_isolation` | Company A creates position; query with Company B | Empty list |
| `test_salary_validation_at_db_level` | service allows it but DB rejects | `IntegrityError` caught and re-raised as `PositionError` 400 |
| `test_update_salary_via_partial` | PATCH with only `base_salary_max` | Existing `base_salary_min` retained; new max vs old min validated |

---

### 5.5 Feature Tests — Position API

> **Note**: The Position API (`apps/apis/v1/positions/`) has not been created yet. These tests define the expected API contract and should be written once the API is implemented, following the same patterns as `DepartmentViewSet`.

#### Expected API endpoints

```
GET    /api/v1/positions/           — list (filterable by department_id, level)
POST   /api/v1/positions/            — create
GET    /api/v1/positions/{id}/       — retrieve
PATCH  /api/v1/positions/{id}/       — partial update
DELETE /api/v1/positions/{id}/       — soft delete
POST   /api/v1/positions/{id}/restore/ — restore
```

#### Happy-path (assuming `PositionViewSet` mirrors `DepartmentViewSet`)

| Test | Request | Expected Result |
|---|---|---|
| `test_list_positions` | `GET /api/v1/positions/` | 200, paginated |
| `test_list_with_department_filter` | `GET /api/v1/positions/?department_id=<uuid>` | 200, filtered |
| `test_list_with_level_filter` | `GET /api/v1/positions/?level=manager` | 200, filtered |
| `test_create_position` | `POST` + full payload | 201 |
| `test_retrieve_position` | `GET /api/v1/positions/{id}/` | 200 |
| `test_partial_update` | `PATCH` + `{title: "..."}` | 200 |
| `test_delete_position` | `DELETE` | 204 |
| `test_restore_position` | `POST restore/` | 200 |

#### Negative-path

| Test | Request | Expected Result |
|---|---|---|
| `test_create_missing_department_id` | `POST` without `department_id` | 400 |
| `test_create_missing_title` | `POST` without `title` | 400 |
| `test_create_salary_min_greater_than_max` | Pydantic validator rejects at schema level | 400 + validation error |
| `test_create_department_not_found` | non-existent `department_id` | 400/404 |
| `test_retrieve_not_found` | unknown UUID | 404 |
| `test_update_salary_breach` | new min > existing max | 400 |
| `test_update_department_wrong_company` | dept from other company | 400/404 |

#### Permission Tests — Position API

Mirror the Department permission matrix, replacing `/departments/` with `/positions/`. All write operations (`create`, `patch`, `delete`, `restore`) require `IsHRAdmin`. Read operations (`list`, `retrieve`) are `IsAuthenticated`.

---

## 6. Schema Tests (`test_department_schemas.py`)

| Test | Input | Expected Result |
|---|---|---|
| `test_department_create_request_code_uppercase` | `code="eng"` | Pydantic validator uppercases to `"ENG"` |
| `test_department_create_request_trims_whitespace` | `code="  ENG  "` | Trimmed to `"ENG"` |
| `test_department_update_request_code_uppercase` | `code="be"` in update | Uppercased to `"BE"` |
| `test_department_update_request_null_code` | `code=None` | `None` preserved (optional field) |
| `test_position_create_min_less_than_max` | `min=5M, max=8M` | Valid |
| `test_position_create_min_greater_than_max` | `min=10M, max=5M` | `ValueError` rejected by validator |
| `test_position_create_equality_allowed` | `min=5M, max=5M` | Valid |
| `test_position_update_partial_min` | only `base_salary_min` provided | Validator passes (optional) |
| `test_position_update_both_salary_fields` | both provided and valid | Validator passes |

---

## 7. Summary Checklist

### Files to create

```
apps/departments/tests/
├── __init__.py
├── conftest.py          # department + position fixtures
├── test_department_service.py      # unit
├── test_department_selectors.py     # unit
├── test_department_models.py        # unit
├── test_department_integration.py  # integration
├── test_department_api.py           # feature
├── test_department_permissions.py   # feature
├── test_department_schemas.py       # unit
├── test_position_service.py         # unit
├── test_position_selectors.py       # unit
├── test_position_models.py          # unit
├── test_position_integration.py     # integration
├── test_position_api.py             # feature (after PositionViewSet exists)
└── test_position_permissions.py     # feature
```

### Test count estimate

| Category | Department | Position | Total |
|---|---|---|---|
| Unit | ~18 | ~22 | ~40 |
| Integration | ~4 | ~5 | ~9 |
| Feature (API) | ~14 | ~14 | ~28 |
| Feature (Permissions) | ~18 combos | ~18 combos | ~36 combos |
| Schema | ~8 | ~9 | ~17 |
| **Total** | | | **~130 tests** |

---

## 8. Fixtures Reused from `tests/factories.py`

The existing factories cover what the department tests need with minimal additions:

| Factory | Used for |
|---|---|
| `CompanyFactory` | `department.company`, `position.company` |
| `DepartmentFactory` | Only as a base — its `code` field requires explicit set |
| `PositionFactory` | Only as a base — requires explicit `department`, `level`, salary fields |
| `HRAdminFactory` | `hr_admin_client` |
| `ManagerFactory` | `manager_client` |
| `EmployeeUserFactory` | `employee_client` |
| `HSEOfficerFactory` | `hse_officer_client` |
| `PlatformAdminFactory` | `platform_admin_client` |
| `CompanyFactory` (second call) | `other_company_client` |

The `DepartmentFactory` and `PositionFactory` stubs in `tests/factories.py` need to be **enhanced** to include required fields:

```python
# Update DepartmentFactory in tests/factories.py:
class DepartmentFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Department {n}")
    code = factory.Sequence(lambda n: f"DEPT{n:03d}")
    company = factory.SubFactory(CompanyFactory)

# Update PositionFactory in tests/factories.py:
class PositionFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: f"Position {n}")
    level = "staff"
    base_salary_min = Decimal("5000000")
    base_salary_max = Decimal("8000000")
    company = factory.SubFactory(CompanyFactory)
    # department must be set explicitly via factory.LazyAttribute or in test
```

---

## 9. Notes

- **Position API is not yet implemented** — `test_position_api.py` and `test_position_permissions.py` should be written *after* `apps/apis/v1/positions/views.py` is created.
- **Cross-tenant 403 vs 404 rule**: always assert 403 for cross-company access attempts — never 404. This prevents ID enumeration attacks.
- **Salary band constants** (`constants.py`) can be tested against known values — e.g., `"staff"` maps to `min=3_000_000, max=5_000_000`.
- **Choices** (`choices.py`) are enum classes — their string values can be asserted directly; no logic to test but useful as test data seeds.
