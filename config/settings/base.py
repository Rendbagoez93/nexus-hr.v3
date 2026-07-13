"""
Base Django settings — consumed by local.py and production.py.

Import envcommon values first, then layer Django-specific settings on top.
"""

from datetime import timedelta
from pathlib import Path

from .envcommon import get_env
from .logging import build_logging_config, configure_structlog

env = get_env()

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # nexus-hr.v3/


# ── Core ──────────────────────────────────────────────────────────────────────
SECRET_KEY = env.SECRET_KEY
DEBUG = env.DEBUG
ALLOWED_HOSTS = env.ALLOWED_HOSTS

# ── Application registry ──────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "django_celery_beat",
    "django_celery_results",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.shared",
    "apps.companies",
    "apps.users",
    "apps.audit",
    "apps.departments",
    "apps.documents",
    "apps.employees",
    "apps.attendance",
    "apps.hse",
    "apps.payroll",
    "apps.apis",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_structlog.middlewares.request.RequestMiddleware",
    "apps.shared.middleware.tenant_middleware.TenantMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.shared.context_processors.nexus_global",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.DB_NAME,
        "USER": env.DB_USER,
        "PASSWORD": env.DB_PASSWORD,
        "HOST": env.DB_HOST,
        "PORT": str(env.DB_PORT),
    }
}


# ── Auth ─────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.AuthUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "id-ID"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True


# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]


# ── Media files ───────────────────────────────────────────────────────────────
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "apps.apis.v1.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.shared.utils.pagination.NexusPaginator",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.shared.exceptions.nexus_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
    "DATE_FORMAT": "%Y-%m-%d",
}


# ── Simple JWT ─────────────────────────────────────────────────────────────────
# JWT settings will be configured in Phase 3
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.JWT_ACCESS_TOKEN_LIFETIME_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.JWT_REFRESH_TOKEN_LIFETIME_DAYS),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    # "TOKEN_OBTAIN_SERIALIZER": "apps.apis.v1.authentication.serializers.TokenObtainPairSerializer",
}


# ── DRF Spectacular (OpenAPI) ─────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Nexus HR API",
    "VERSION": "1.0.0",
    "DESCRIPTION": "Nexus HR — Centralized Employee Data Management",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}


# # ── Celery ────────────────────────────────────────────────────────────────────
# CELERY_BROKER_URL = env.celery_broker_url
# CELERY_RESULT_BACKEND = env.celery_result_backend
# CELERY_ACCEPT_CONTENT = ["json"]
# CELERY_TASK_SERIALIZER = "json"
# CELERY_RESULT_SERIALIZER = "json"
# CELERY_TIMEZONE = TIME_ZONE
# CELERY_TASK_TRACK_STARTED = True
# CELERY_RESULT_EXTENDED = True
# CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes per task
# CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"


# ── Caches ───────────────────────────────────────────────────────────────────
# Development: Use local memory cache (simple, no Redis required)
# Production: Uncomment Redis cache after enabling redis service in docker-compose.yml
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "nexus-cache",
    }
}

# PRODUCTION — Redis cache (requires redis service in docker-compose.yml)
# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.redis.RedisCache",
#         "LOCATION": env.redis_url,
#     }
# }


# # ── S3 Storage (django-storages) ───────────────────────────────────────────────
# USE_S3 = bool(env.aws_access_key_id and env.aws_s3_bucket_name)

# if USE_S3:
#     STORAGES = {
#         "default": {
#             "BACKEND": "storages.backends.s3.S3Storage",
#         },
#         "staticfiles": {
#             "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
#         },
#     }
#     AWS_S3_ACCESS_KEY_ID = env.aws_access_key_id
#     AWS_S3_SECRET_ACCESS_KEY = env.aws_secret_access_key
#     AWS_S3_BUCKET_NAME = env.aws_s3_bucket_name
#     AWS_S3_ENDPOINT_URL = env.aws_s3_endpoint_url
#     AWS_S3_REGION_NAME = env.aws_s3_region_name
#     AWS_S3_FILE_OVERWRITE = False
#     AWS_DEFAULT_ACL = "private"
#     AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
# else:
#     STORAGES = {
#         "default": {
#             "BACKEND": "django.core.files.storage.FileSystemStorage",
#         },
#         "staticfiles": {
#             "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
#         },
#     }


# ── Structured Logging (structlog + django-structlog) ─────────────────────────
LOG_LEVEL = env.LOG_LEVEL

configure_structlog()
LOGGING = build_logging_config(debug=DEBUG, log_level=LOG_LEVEL)
