"""
Production settings.

- DEBUG=False
- S3 media storage
- SMTP email
- Sentry error tracking
"""

from .base import *

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in env.allowed_hosts.split(",") if h.strip()]

# ── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.email_host
EMAIL_PORT = env.email_port
EMAIL_HOST_USER = env.email_host_user
EMAIL_HOST_PASSWORD = env.email_host_password
EMAIL_USE_TLS = env.email_use_tls
DEFAULT_FROM_EMAIL = env.email_from

# ── Sentry ───────────────────────────────────────────────────────────────────
if env.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=env.sentry_dsn,
        environment=env.sentry_environment,
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
        "LOCATION": env.redis_url,
    }
}
