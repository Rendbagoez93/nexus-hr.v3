"""
Local development settings.

- DEBUG=True
- Console email backend
- File-based media storage
- Verbose logging
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Email: console backend (prints to stdout, no real sending)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Override caches to locmem for local dev (no Redis required)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# Allow all hosts in local dev
ALLOWED_HOSTS = ["*"]

# Celery: eager mode (tasks run synchronously in-process, no broker needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Staticfiles served by Whitenoise in dev (no S3)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Add whitenoise for static serving in development
try:
    import whitenoise
except ImportError:
    pass
else:
    MIDDLEWARE = [m for m in MIDDLEWARE if m != "django.middleware.security.SecurityMiddleware"] + [
        "whitenoise.middleware.WhiteNoiseMiddleware"
    ]

    # Allow whitenoise to serve static files without STATIC_ROOT set
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
