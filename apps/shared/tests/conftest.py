"""
apps/shared/tests/conftest.py — Shared fixtures for apps/shared tests.

Fixtures here are scoped to function (the default) since shared utilities
tests don't need to reuse expensive setup across a module.
"""

from __future__ import annotations

import pytest

@pytest.fixture
def company(db):
    """A single active Company instance."""
    from apps.companies.models import Company
    return Company.objects.create(
        name="Test Company",
        industry="manufacturing",
        subscription_tier="core",
        is_active=True,
    )


@pytest.fixture
def two_companies(db):
    """Two distinct active Company instances for cross-tenant isolation tests."""
    from apps.companies.models import Company
    company_a = Company.objects.create(
        name="Company Alpha",
        industry="manufacturing",
        subscription_tier="core",
        is_active=True,
        emp_number_prefix="ALP",
    )
    company_b = Company.objects.create(
        name="Company Beta",
        industry="construction",
        subscription_tier="payroll",
        is_active=True,
        emp_number_prefix="BTX",
    )
    return company_a, company_b
