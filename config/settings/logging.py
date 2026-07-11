import structlog

shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
    structlog.stdlib.ExtraAdder(),
]


def configure_structlog() -> None:
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def build_logging_config(*, debug: bool, log_level: str) -> dict:
    renderer = structlog.dev.ConsoleRenderer(colors=True) if debug else structlog.processors.JSONRenderer()
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    renderer,
                ],
                "foreign_pre_chain": shared_processors,
            },
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "structured"},
        },
        "root": {"handlers": ["console"], "level": "WARNING"},
        "loggers": {
            "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
            "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
            "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
            "nexus": {"handlers": ["console"], "level": log_level, "propagate": False},
            "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "django_structlog": {"handlers": ["console"], "level": "INFO", "propagate": False},
        },
    }
