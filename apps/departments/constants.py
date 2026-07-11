"""
apps/departments/constants.py

Business constants for the departments module.
Default salary bands are monthly (Indonesian Rupiah).
"""

from decimal import Decimal


# Default salary band ranges per level (monthly, IDR)
SALARY_BANDS: dict[str, dict[str, Decimal]] = {
    "staff": {"min": Decimal("3000000"), "max": Decimal("5000000")},
    "supervisor": {"min": Decimal("5000000"), "max": Decimal("8000000")},
    "assistant_manager": {"min": Decimal("8000000"), "max": Decimal("12000000")},
    "manager": {"min": Decimal("12000000"), "max": Decimal("20000000")},
    "senior_manager": {"min": Decimal("20000000"), "max": Decimal("35000000")},
    "general_manager": {"min": Decimal("35000000"), "max": Decimal("60000000")},
    "director": {"min": Decimal("60000000"), "max": Decimal("150000000")},
    "c_level": {"min": Decimal("100000000"), "max": Decimal("500000000")},
}

DEFAULT_SALARY_BAND_LEVEL: str = "staff"
