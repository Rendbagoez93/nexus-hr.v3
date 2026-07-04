"""
apps/shared/logging/context.py

Context binding for structlog — request / task / tenant scoping.
"""

import threading
from typing import Any

_thread_locals = threading.local()


def bind_request_context(
    request_id: str | None = None,
    user_id: int | None = None,
    company_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Bind HTTP request context to thread-local storage for logging."""
    _thread_locals.context = {
        "request_id": request_id,
        "user_id": user_id,
        "company_id": company_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }


def bind_task_context(
    task_id: str | None = None,
    company_id: int | None = None,
    user_id: int | None = None,
) -> None:
    """Bind Celery task context to thread-local storage for logging."""
    _thread_locals.context = {
        "task_id": task_id,
        "company_id": company_id,
        "user_id": user_id,
    }


def get_request_context() -> dict[str, Any]:
    """Return the current thread-local context dict."""
    return getattr(_thread_locals, "context", {})


def clear_context() -> None:
    """Clear all thread-local context (call after request/task completes)."""
    _thread_locals.context = {}
