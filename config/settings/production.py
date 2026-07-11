"""
Production settings.

- DEBUG=False
- S3 media storage
- SMTP email
- Sentry error tracking
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# env.ALLOWED_HOSTS is already a parsed list[str] (comma-separated .env values
# are split by the ALLOWED_HOSTS validator in envcommon.py).
ALLOWED_HOSTS = env.ALLOWED_HOSTS

# ── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.EMAIL_HOST
EMAIL_PORT = env.EMAIL_PORT
EMAIL_HOST_USER = env.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = env.EMAIL_HOST_PASSWORD
EMAIL_USE_TLS = env.EMAIL_USE_TLS
DEFAULT_FROM_EMAIL = env.EMAIL_FROM

# ── Sentry ───────────────────────────────────────────────────────────────────
if env.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=env.SENTRY_DSN,
        environment=env.SENTRY_ENVIRONMENT,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.05,
        send_default_pii=False,
    )

# ── Security ─────────────────────────────────────────────────────────────────
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ── Celery — real broker in production ───────────────────────────────────────
CELERY_TASK_ALWAYS_EAGER = False

# ── Caches — Redis ───────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env.REDIS_URL,
    }
}
