"""
apps/shared/tests/test_utils.py

Phase 1 — Shared utility function tests.
Tests date helpers and security helpers from apps/shared/utils/.

Markers:
  unit — Pure function tests with no DB or network I/O
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest

from apps.shared.utils.dates import (
    add_business_days,
    days_until,
    end_of_day,
    end_of_month,
    get_current_date,
    get_current_utc_datetime,
    is_date_expired,
    start_of_day,
    start_of_month,
)
from apps.shared.utils.security import generate_secure_token, mask_email, mask_sensitive_value

pytestmark = pytest.mark.unit


# =============================================================================
# UNIT TESTS — Date Utilities
# =============================================================================

class TestGetCurrentUtcDatetime:
    """get_current_utc_datetime() returns a timezone-aware UTC datetime."""

    def test_returns_utc_datetime(self):
        result = get_current_utc_datetime()
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_now_is_recent(self):
        result = get_current_utc_datetime()
        # Within 5 seconds of now
        now = datetime.now(timezone.utc)
        assert abs((now - result).total_seconds()) < 5


class TestGetCurrentDate:
    """get_current_date() returns today's UTC date."""

    def test_returns_date_object(self):
        result = get_current_date()
        assert isinstance(result, date)
        assert result == datetime.now(timezone.utc).date()


class TestDaysUntil:
    """days_until() returns signed integer days from today."""

    def test_future_date_positive(self):
        today = get_current_date()
        future = today + timedelta(days=10)
        assert days_until(future) == 10

    def test_past_date_negative(self):
        today = get_current_date()
        past = today - timedelta(days=5)
        assert days_until(past) == -5

    def test_today_returns_zero(self):
        today = get_current_date()
        assert days_until(today) == 0

    def test_with_datetime_input(self):
        today = get_current_date()
        future_dt = datetime.combine(
            today + timedelta(days=7),
            time(12, 0),
            tzinfo=timezone.utc,
        )
        assert days_until(future_dt) == 7


class TestIsDateExpired:
    """is_date_expired() returns True for past dates."""

    def test_past_date_is_expired(self):
        yesterday = get_current_date() - timedelta(days=1)
        assert is_date_expired(yesterday) is True

    def test_future_date_is_not_expired(self):
        tomorrow = get_current_date() + timedelta(days=1)
        assert is_date_expired(tomorrow) is False

    def test_today_is_not_expired(self):
        today = get_current_date()
        assert is_date_expired(today) is False

    def test_none_returns_false(self):
        assert is_date_expired(None) is False

    def test_with_datetime_input(self):
        # Use a datetime definitely in the past (24 hours ago)
        yesterday_dt = datetime.now(timezone.utc) - timedelta(hours=24)
        assert is_date_expired(yesterday_dt) is True


class TestAddBusinessDays:
    """add_business_days() skips weekends."""

    def test_add_business_days_skip_weekends(self):
        # Monday + 1 business day = Tuesday
        monday = date(2026, 7, 7)
        tuesday = add_business_days(monday, 1)
        assert tuesday == date(2026, 7, 8)

    def test_add_business_days_skip_weekend(self):
        # Friday + 1 business day = Monday (skip Sat/Sun)
        friday = date(2026, 7, 10)
        monday = add_business_days(friday, 1)
        assert monday == date(2026, 7, 13)

    def test_add_business_days_multiple(self):
        # Monday + 5 business days = Monday next week
        monday = date(2026, 7, 7)
        next_monday = add_business_days(monday, 5)
        assert next_monday == date(2026, 7, 14)

    def test_subtract_business_days(self):
        # Tuesday - 1 business day = Monday
        tuesday = date(2026, 7, 7)  # July 7, 2026 is Tuesday
        monday = add_business_days(tuesday, -1)
        assert monday == date(2026, 7, 6)  # Monday July 6

    def test_zero_business_days_returns_same_day(self):
        any_day = date(2026, 7, 10)
        assert add_business_days(any_day, 0) == any_day


class TestStartOfMonth:
    """start_of_month() returns the first day of the month."""

    def test_mid_month(self):
        result = start_of_month(date(2026, 7, 15))
        assert result == date(2026, 7, 1)

    def test_first_day_unchanged(self):
        result = start_of_month(date(2026, 7, 1))
        assert result == date(2026, 7, 1)

    def test_with_datetime(self):
        result = start_of_month(datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc))
        assert result == date(2026, 7, 1)

    def test_no_arg_uses_today(self):
        result = start_of_month()
        assert result == get_current_date().replace(day=1)


class TestEndOfMonth:
    """end_of_month() returns the last day of the month."""

    def test_july(self):
        result = end_of_month(date(2026, 7, 15))
        assert result == date(2026, 7, 31)

    def test_february_leap_year(self):
        result = end_of_month(date(2024, 2, 10))
        assert result == date(2024, 2, 29)

    def test_february_non_leap_year(self):
        result = end_of_month(date(2025, 2, 10))
        assert result == date(2025, 2, 28)

    def test_december(self):
        result = end_of_month(date(2026, 12, 25))
        assert result == date(2026, 12, 31)

    def test_no_arg_uses_today(self):
        result = end_of_month()
        today = get_current_date()
        expected = date(today.year, today.month, 31)
        assert result == expected


class TestStartOfDay:
    """start_of_day() returns 00:00:00 of the given date."""

    def test_returns_datetime(self):
        result = start_of_day(date(2026, 7, 15))
        assert isinstance(result, datetime)
        assert result.date() == date(2026, 7, 15)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_preserves_timezone(self):
        result = start_of_day(date(2026, 7, 15))
        assert result.tzinfo == timezone.utc

    def test_datetime_truncates_time(self):
        dt = datetime(2026, 7, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = start_of_day(dt)
        assert result == datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc)

    def test_no_arg_uses_now(self):
        result = start_of_day()
        now = get_current_utc_datetime()
        assert result.date() == now.date()
        assert result.hour == 0


class TestEndOfDay:
    """end_of_day() returns 23:59:59.999999 of the given date."""

    def test_returns_datetime(self):
        result = end_of_day(date(2026, 7, 15))
        assert isinstance(result, datetime)
        assert result.date() == date(2026, 7, 15)
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    def test_preserves_timezone(self):
        result = end_of_day(date(2026, 7, 15))
        assert result.tzinfo == timezone.utc

    def test_datetime_truncates_time(self):
        dt = datetime(2026, 7, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = end_of_day(dt)
        assert result == datetime(2026, 7, 15, 23, 59, 59, 999999, tzinfo=timezone.utc)


# =============================================================================
# UNIT TESTS — Security Utilities
# =============================================================================

class TestGenerateSecureToken:
    """generate_secure_token() produces cryptographically random tokens."""

    def test_default_length(self):
        token = generate_secure_token()
        # Default length 32 bytes → ~43 chars URL-safe base64
        assert len(token) >= 40

    def test_custom_length(self):
        token = generate_secure_token(length=16)
        assert len(token) >= 20  # URL-safe base64 padding

    def test_each_call_is_unique(self):
        tokens = [generate_secure_token() for _ in range(100)]
        assert len(set(tokens)) == 100

    def test_is_url_safe(self):
        token = generate_secure_token()
        # No +, /, or = characters
        assert "+" not in token
        assert "/" not in token
        assert "=" not in token


class TestMaskSensitiveValue:
    """mask_sensitive_value() reveals only last N characters."""

    @pytest.mark.parametrize(
        "value, visible_chars, expected",
        [
            ("secret123456", 4, "********3456"),
            ("secret123456", 6, "******123456"),
            ("abc", 4, "***"),
            ("ab", 10, "**"),
            ("abcd", 4, "****"),
            ("secret", 0, "******"),
            ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjN9", 4, "*********************************MjN9"),
        ]
    )
    
    def test_masking_by_length_and_visible_chars(self, value, visible_chars, expected):
        result = mask_sensitive_value(value, visible_chars=visible_chars)
        assert result == expected

    def test_default_visible_chars_is_4(self):
        result = mask_sensitive_value("secret123456")
        assert result == "********3456"

    def test_empty_string(self):
        result = mask_sensitive_value("") 
        assert result == ""

    def test_none_value(self):
        result = mask_sensitive_value(None)
        assert result == ""

    def test_token_like_value(self):
        result = mask_sensitive_value("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjN9")
        assert "eyJ" not in result
        # last 4 chars of the RAW string, not the decoded JWT payload
        assert result.endswith("MjN9")

    def test_return_type_is_str(self):
        result = mask_sensitive_value("secret123456")
        assert isinstance(result, str)
    
class TestMaskEmail:
    """mask_email() obscures email for safe display."""

    def test_standard_email(self):
        result = mask_email("john.doe@example.com")
        assert "john" not in result or result.count("*") > 0
        assert "@" in result
        assert "example.com" not in result

    def test_short_local_part(self):
        result = mask_email("ab@example.com")
        assert "@" in result
        assert "*****" in result

    def test_empty_email(self):
        result = mask_email("")
        assert result == "****"

    def test_no_at_symbol(self):
        result = mask_email("notanemail")
        assert result == "****"

    def test_none_email(self):
        result = mask_email(None)
        assert result == "****"

    def test_preserves_email_structure(self):
        """Masked email contains @ and hides the local and domain parts."""
        result = mask_email("user@company.co.uk")
        # Must contain @ symbol
        assert "@" in result
        # Must not expose the original local part "user"
        assert "user" not in result
        # Must not expose the full original domain "company.co.uk"
        assert "company.co.uk" not in result
        # Must be shorter than the original
        assert len(result) < len("user@company.co.uk")
