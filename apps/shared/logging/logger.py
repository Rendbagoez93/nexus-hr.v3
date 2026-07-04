"""
apps/shared/logging/logger.py

Structured logger for the Nexus domain.
"""

import functools
import logging
import time
import uuid
from typing import Any, Callable, TypeVar

import structlog

from apps.shared.logging.context import get_request_context

F = TypeVar("F", bound=Callable[..., Any])


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a structlog logger bound to 'nexus.{name}'.

    Usage:
        log = get_logger("employee")
        log.info("employee_created", employee_id=emp.id)
    """
    logger_name = f"nexus.{name}" if name else "nexus"
    return structlog.get_logger(logger_name)


def log_function_call(
    func: F,
) -> F:
    """
    Decorator that logs entry/exit of service functions with timing.

    Usage:
        @log_function_call
        def create_employee(company_id, data):
            ...
    """
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = get_request_context()
        call_id = str(uuid.uuid4())[:8]
        logger.debug(
            "function_call.start",
            function=func.__name__,
            call_id=call_id,
            request_id=ctx.get("request_id"),
            company_id=ctx.get("company_id"),
        )
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(
                "function_call.complete",
                function=func.__name__,
                call_id=call_id,
                elapsed_ms=round(elapsed, 2),
            )
            return result
        except Exception:  # noqa: BLE001
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception(
                "function_call.error",
                function=func.__name__,
                call_id=call_id,
                elapsed_ms=round(elapsed, 2),
            )
            raise

    return wrapper  # type: ignore[return-type]
