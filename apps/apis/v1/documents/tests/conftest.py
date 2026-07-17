"""
apps/apis/v1/documents/tests/conftest.py

Re-exports fixtures from apps/documents/tests/conftest.py (which itself
re-exports from apps/employees/tests/conftest.py) so they are visible to
tests in this directory (pytest only auto-loads conftest from the test
directory and its parent directories, not sibling sub-trees).
"""

from apps.documents.tests.conftest import *  # noqa: F401, F403

# Re-export explicitly to make fixture resolution unambiguous
from apps.documents.tests.conftest import (  # noqa: F401
    company,
    department,
    document,
    document_for_linked_employee,
    document_other_company,
    employee,
    employee_client,
    employee_other_company,
    employee_with_user,
    hr_admin_client,
    inactive_document,
    manager_client,
    other_company_client,
    platform_admin_client,
    position,
    two_documents,
    uploaded_file,
    verified_document,
)

# api_client lives in tests/conftest.py — re-export it here so this conftest
# shadows the tests/conftest.py one (which uses a bare factory-created user
# not tied to our company fixture)
from tests.conftest import api_client  # noqa: F401
