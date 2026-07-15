"""
apps/apis/v1/employees/tests/conftest.py

Re-exports fixtures from apps/employees/tests/conftest.py so they are visible
to tests in this directory (pytest only auto-loads conftest from the test
directory and its parent directories, not sibling sub-trees).
"""

from apps.employees.tests.conftest import *  # noqa: F401, F403

# Re-export explicitly to make fixture resolution unambiguous
from apps.employees.tests.conftest import (
    company,
    department,
    position,
    employee,
    employee_other_company,
    inactive_employee,
    resigned_employee,
    terminated_employee,
    probation_employee,
    contract_employee,
    employee_with_user,
    two_employees,
    two_companies,
    hr_admin_client,
    manager_client,
    employee_client,
    other_company_client,
    platform_admin_client,
)

# api_client lives in tests/conftest.py — re-export it here so this conftest
# shadows the tests/conftest.py one (which uses a bare factory-created user
# not tied to our company fixture)
from tests.conftest import api_client
