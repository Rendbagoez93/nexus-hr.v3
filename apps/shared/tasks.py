"""
apps/shared/tasks.py

Base Celery task class with structured logging and common configuration.
"""

from typing import Any

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from structlog import BoundLogger

from apps.shared.logging.context import get_request_context
from apps.shared.logging.logger import get_logger


class NexusTask(Task):
    """
    Base Celery task class for all Nexus background jobs.

    Features:
        - Structured logging bound to task_id and company_id
        - Soft time limit (30 min default)
        - Hard time limit (35 min default)
        - Automatic retry on connection errors
        - Request context propagation from parent thread
    """

    autoretry_for = (ConnectionError, TimeoutError)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 5

    # Time limits in seconds (override per-task if needed)
    soft_time_limit = 30 * 60  # 30 minutes
    time_limit = 35 * 60  # 35 minutes

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # Propagate request context from the calling thread
        ctx = get_request_context()
        task_id = self.request.id

        log: BoundLogger = get_logger(self.name)
        log = log.bind(task_id=task_id, company_id=ctx.get("company_id"))

        try:
            return super().__call__(*args, **kwargs)
        except SoftTimeLimitExceeded:
            log.error("task.soft_time_limit_exceeded", task=self.name)
            raise
        except ConnectionError as e:
            log.warning("task.connection_error", task=self.name, error=str(e))
            raise

    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, **fkwargs) -> None:
        log = get_logger(self.name).bind(task_id=task_id)
        log.exception("task.failed", exception=str(exc))

    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict, **fkwargs) -> None:
        log = get_logger(self.name).bind(task_id=task_id)
        log.info("task.completed", result=str(retval)[:200])

    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, **fkwargs) -> None:
        log = get_logger(self.name).bind(task_id=task_id)
        log.warning("task.retrying", exception=str(exc), attempt=self.request.retries)
