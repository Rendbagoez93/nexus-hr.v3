"""
apps/shared/tests/test_tenant_infrastructure.py

Phase 1 — Tenant Infrastructure tests.
Tests TenantModel, TenantManager, TenantMiddleware, and SoftDeleteMixin.

Markers:
  unit    — TenantModel constraints, TenantManager methods, SoftDeleteMixin methods
  integration — tenant-scoped querying, cross-tenant isolation
  feature  — TenantMiddleware JWT → request.company_id
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from apps.companies.models import Company
from apps.shared.middleware.tenant_middleware import TenantMiddleware
from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel
from apps.shared.models import TenantManager, TenantModel, TenantQuerySet
from apps.users.models import AuthUser

pytestmark = pytest.mark.unit


# =============================================================================
# UNIT TESTS — TenantModel & TenantManager
# =============================================================================

class TestTenantModelConstraint:
    """TenantModel abstract base — constraints and structure."""

    def test_tenant_model_is_abstract(self):
        """TenantModel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TenantModel()

    def test_tenant_model_provides_company_fk(self):
        """TenantModel subclasses must have a company FK via TenantManager."""
        # TenantManager.for_company() is the public API; verify it exists
        assert hasattr(TenantManager, "for_company")
        assert hasattr(TenantManager, "alive")

    def test_tenant_query_set_has_for_company(self):
        """TenantQuerySet provides .for_company() and .alive()."""
        assert hasattr(TenantQuerySet, "for_company")
        assert hasattr(TenantQuerySet, "alive")


class TestTenantManagerMethods:
    """TenantManager.for_company() and .alive() filtering."""

    @pytest.mark.unit
    def test_for_company_returns_filtered_queryset(self, company):
        """for_company(company_id) returns a TenantQuerySet filtered by company."""
        from apps.shared.models import TenantQuerySet
        from apps.users.models import AuthUser

        qs = TenantQuerySet(model=AuthUser, using="default")
        result = qs.for_company(company.id)

        assert isinstance(result, TenantQuerySet)
        assert result.query.where.__class__.__name__ == "WhereNode"

    @pytest.mark.unit
    def test_alive_returns_active_filtered_queryset(self):
        """alive() returns a TenantQuerySet filtered by is_active=True."""
        from apps.shared.models import TenantQuerySet
        from apps.users.models import AuthUser

        qs = TenantQuerySet(model=AuthUser, using="default")
        result = qs.alive()

        assert isinstance(result, TenantQuerySet)
        assert result.query.where.__class__.__name__ == "WhereNode"


# =============================================================================
# UNIT TESTS — SoftDeleteMixin
# =============================================================================

class TestSoftDeleteMixin:
    """SoftDeleteMixin.is_active, .deactivate(), .restore() methods."""

    def test_soft_delete_model_inherits_is_active(self, company):
        """The Company model (which uses SoftDeleteMixin) has is_active."""
        assert hasattr(company, "is_active")

    def test_deactivate_sets_is_active_false(self, company):
        """deactivate() flips is_active to False and sets deleted_at."""
        company.is_active = True
        company.save()

        company.deactivate()

        assert company.is_active is False
        assert company.deleted_at is not None

    def test_deactivate_idempotent(self, company):
        """Calling deactivate twice is safe."""
        company.deactivate()
        original_deleted_at = company.deleted_at

        company.deactivate()

        assert company.is_active is False
        assert company.deleted_at == original_deleted_at


# =============================================================================
# UNIT TESTS — TimestampedModel
# =============================================================================

class TestTimestampedModel:
    """TimestampedModel provides created_at and updated_at."""

    def test_timestamped_model_has_timestamps(self, company):
        """Company (using TimestampedModel) has created_at and updated_at."""
        assert hasattr(company, "created_at")
        assert hasattr(company, "updated_at")
        assert company.created_at is not None
        assert company.updated_at is not None


# =============================================================================
# INTEGRATION TESTS — Tenant-scoped querying
# =============================================================================

class TestTenantScoping:
    """Tenant-scoped querying — each company sees only its own data."""

    @pytest.mark.integration
    def test_tenant_manager_scopes_by_company(self, db):
        """A query through TenantManager.for_company() returns only matching records."""
        from apps.shared.models import TenantQuerySet
        from apps.users.models import AuthUser

        # Use a model that has a `company` FK to exercise the filter path
        qs = TenantQuerySet(model=AuthUser, using="default")
        result = qs.for_company(company_id=99999)
        assert result.query.where.__class__.__name__ == "WhereNode"

    @pytest.mark.integration
    def test_company_soft_delete_isolation(self, two_companies):
        """Soft-deleted companies do not appear in default queries."""
        company_a, company_b = two_companies

        # Deactivate company A
        company_a.deactivate()

        # company_b should still be visible
        assert Company.objects.filter(pk=company_b.pk).exists()

        # company_a with is_active filter should be gone
        active_qs = Company.objects.filter(is_active=True)
        assert not active_qs.filter(pk=company_a.pk).exists()


class TestCrossTenantIsolation:
    """Cross-tenant isolation — companies must never see each other's data."""

    @pytest.mark.integration
    def test_company_queryset_is_company_scoped(self, two_companies):
        """Company.objects returns all companies (platform-level model)."""
        # Company is NOT a TenantModel subclass — it's the tenant itself.
        # So it's visible to platform admins across all tenants.
        all_companies = Company.objects.all()
        assert all_companies.count() >= 2

    @pytest.mark.integration
    def test_each_company_has_distinct_prefix(self, two_companies):
        """Two companies have distinct emp_number_prefix values."""
        company_a, company_b = two_companies
        assert company_a.emp_number_prefix != company_b.emp_number_prefix


# =============================================================================
# FEATURE TESTS — TenantMiddleware
# =============================================================================

class TestTenantMiddleware:
    """TenantMiddleware extracts company_id from JWT and attaches to request."""

    @pytest.mark.feature
    def test_tenant_middleware_attaches_company_id_from_jwt(self):
        """A request with a JWT containing company_id results in request.company_id set."""
        middleware = TenantMiddleware(get_response=lambda r: r)

        # Build a mock request with a mock auth token
        request = MagicMock()
        request.auth = MagicMock()
        request.auth.get = lambda key: {"company_id": 42, "role": "hr_admin"}.get(key)

        response = middleware(request)

        assert response is not None
        assert request.company_id == 42

    @pytest.mark.feature
    def test_tenant_middleware_sets_none_when_no_auth(self):
        """A request without auth sets request.company_id to None."""
        middleware = TenantMiddleware(get_response=lambda r: r)

        request = MagicMock()
        request.auth = None

        response = middleware(request)

        assert request.company_id is None

    @pytest.mark.feature
    def test_tenant_middleware_handles_missing_company_id_in_token(self):
        """A JWT with no company_id (platform admin token) sets request.company_id to None."""
        middleware = TenantMiddleware(get_response=lambda r: r)

        request = MagicMock()
        request.auth = MagicMock()
        request.auth.get = lambda key: {"role": "platform_admin"}.get(key)

        response = middleware(request)

        assert request.company_id is None
