"""
Base settings shared by every environment.

Environment-specific settings (development.py, production.py) import * from
this module and override only what genuinely differs. Nothing environment-
specific (DEBUG, ALLOWED_HOSTS, secret sourcing) belongs here.
"""
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# config/settings/base.py -> BASE_DIR is the repo root (two levels up).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Core security config (values sourced from environment, never hardcoded)
# ---------------------------------------------------------------------------
SECRET_KEY = config("DJANGO_SECRET_KEY")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
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
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "django_celery_beat",
]

# Domain-separated apps (Section 7 of project context: monolith, app-per-domain).
# Order matters only for migration dependency resolution within Django itself;
# explicit FKs across apps use "app_label.Model" strings so load order is safe.
LOCAL_APPS = [
    "apps.accounts",
    "apps.core",
    "apps.customers",
    "apps.leads",
    "apps.projects",
    "apps.invoices",
    "apps.billing",
    "apps.documents",
    "apps.notifications",
    "apps.analytics",
    "apps.platform_admin",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.authentication.BaselineAuthBackend",
    "django.contrib.auth.backends.ModelBackend",  # fallback: Django admin login, createsuperuser
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
# Order matters:
#   - CorsMiddleware must sit high, before CommonMiddleware.
#   - TenantContextMiddleware must run AFTER AuthenticationMiddleware (it needs
#     request.user to resolve the active Membership) and BEFORE any view code
#     executes, since every tenant-scoped queryset depends on the contextvar
#     it sets. It also issues `SET LOCAL app.tenant_id` for the Postgres RLS
#     backstop, so it must run inside the per-request DB transaction.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.TenantContextMiddleware",
    "apps.core.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# PostgreSQL is a hard requirement, not a preference: the tenant-isolation
# design (Section 7 of project context) relies on Postgres Row-Level Security
# as the backstop layer. Do not swap this for sqlite/mysql.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
        "OPTIONS": {
            "options": "-c statement_timeout=15000",  # 15s hard query cap
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# ---------------------------------------------------------------------------
# Media files (Document uploads) — local filesystem storage for now. No
# hosting/infra provider is confirmed yet (project context Section 10,
# still open); swapping to S3-compatible object storage is a `STORAGES`
# settings change, not a model/view change — see apps/documents/models.py.
# ---------------------------------------------------------------------------
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Email (invitations, notifications) — provider not yet selected per project
# context (Section 3a); console backend as the safe, always-working default
# until a transactional provider is confirmed.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@baseline.app")

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/hour",
        "anon": "100/hour",
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.baseline_exception_handler",
}

SIMPLE_JWT = {
    # Short-lived access token: the tenant-context middleware re-validates
    # Membership from the DB on every request regardless (Section 4 of
    # project context — never trust a stale token claim), but a short TTL
    # limits the blast radius of a leaked token.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Logging — structured, JSON-friendly. Observability provider not yet
# selected (project context Section 2), but a real config belongs here from
# day one rather than left as Django's bare-bones default.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s "
            "[tenant=%(tenant_id)s] %(message)s",
            "defaults": {"tenant_id": "-"},
        },
    },
    "filters": {
        "tenant_context": {
            "()": "apps.core.logging_filters.TenantContextFilter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["tenant_context"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": config("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# Celery — background/scheduled jobs. Two periodic tasks exist today:
# invoice overdue detection (apps/invoices/tasks.py) and task-due-soon
# notifications (apps/projects/tasks.py) — these are what actually fire
# Notification.NotificationType.INVOICE_OVERDUE / TASK_DUE_SOON, which were
# previously defined as choices but never triggered anywhere.
# ---------------------------------------------------------------------------
from celery.schedules import crontab  # noqa: E402

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 5 * 60  # hard kill a stuck task after 5 minutes
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_BEAT_SCHEDULE = {
    "check-overdue-invoices-hourly": {
        "task": "apps.invoices.tasks.check_overdue_invoices",
        "schedule": crontab(minute=0),  # top of every hour
    },
    "notify-tasks-due-soon-daily": {
        "task": "apps.projects.tasks.notify_tasks_due_soon",
        "schedule": crontab(hour=8, minute=0),  # 08:00 UTC daily
    },
}

# ---------------------------------------------------------------------------
# Baseline-specific settings
# ---------------------------------------------------------------------------
# Billing providers (project context Section 3): dual-provider, Paystack +
# Opay, both normalizing into the same Entitlement write path.
PAYSTACK_SECRET_KEY = config("PAYSTACK_SECRET_KEY", default="")
PAYSTACK_WEBHOOK_SECRET = config("PAYSTACK_WEBHOOK_SECRET", default="")
OPAY_SECRET_KEY = config("OPAY_SECRET_KEY", default="")
OPAY_WEBHOOK_SECRET = config("OPAY_WEBHOOK_SECRET", default="")

# Invitation token TTL (project context Section 4): 7-day expiry, confirmed.
INVITATION_TOKEN_TTL_DAYS = 7

# NDPA (project context Section 8): hard-delete capability must exist for
# data-subject requests — this flag exists so it can be asserted on in tests
# and is never silently turned into a soft-delete no-op.
NDPA_HARD_DELETE_ENABLED = True
