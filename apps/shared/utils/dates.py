"""
apps/shared/utils/dates.py

Date/time helpers. All timestamps are UTC-aware.
"""

from datetime import date, datetime, time, timedelta, timezone

from dateutil.relativedelta import relativedelta


def get_current_utc_datetime() -> datetime:
    return datetime.now(timezone.utc)


def get_current_date() -> date:
    return get_current_utc_datetime().date()


def days_until(target: date | datetime) -> int:
    """Returns positive int for future dates, negative for past, 0 for today."""
    if isinstance(target, datetime):
        target = target.date()
    return (target - get_current_date()).days


def is_date_expired(expiry_date: date | datetime | None) -> bool:
    if expiry_date is None:
        return False
    if isinstance(expiry_date, datetime):
        expiry_date = expiry_date.date()
    return expiry_date < get_current_date()


def add_business_days(start: date, days: int) -> date:
    """Add calendar days, skipping weekends."""
    current = start
    direction = 1 if days >= 0 else -1
    remaining = abs(days)
    while remaining > 0:
        current += timedelta(days=direction)
        if current.weekday() < 5:
            remaining -= 1
    return current


def start_of_month(dt: date | datetime | None = None) -> date:
    if dt is None:
        dt = get_current_date()
    if isinstance(dt, datetime):
        dt = dt.date()
    return dt.replace(day=1)


def end_of_month(dt: date | datetime | None = None) -> date:
    if dt is None:
        dt = get_current_date()
    if isinstance(dt, datetime):
        dt = dt.date()
    return dt + relativedelta(day=31)


def start_of_day(dt: date | datetime | None = None) -> datetime:
    if dt is None:
        return get_current_utc_datetime().replace(hour=0, minute=0, second=0, microsecond=0)
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return datetime.combine(dt, time.min, tzinfo=timezone.utc)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: date | datetime | None = None) -> datetime:
    if dt is None:
        return get_current_utc_datetime().replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return datetime.combine(dt, time.max, tzinfo=timezone.utc)
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
