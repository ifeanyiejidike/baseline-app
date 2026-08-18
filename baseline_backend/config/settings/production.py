"""
Production settings.

Every value that could silently degrade security has an explicit, fail-loud
default via python-decouple: missing required env vars raise on startup
rather than falling back to an insecure default.
"""
from decouple import Csv, config

from .base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())  # required, no default

# --- Transport security --------------------------------------------------
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Session/CSRF cookies: HttpOnly + SameSite as a CSRF/XSS defense-in-depth
# layer (in addition to CsrfViewMiddleware).
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # CSRF cookie must be JS-readable for the SPA to send it as a header
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- CORS: explicit allow-list only, no wildcard in production ----------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv())  # required

# --- Static files served via whitenoise/CDN upstream ----------------------
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

# --- Error tracking --------------------------------------------------------
# Sentry DSN intentionally read here, not in base.py: error tracking should
# only ever be active where DEBUG is False. No hosting/observability
# provider is confirmed yet (project context Section 10) — this stays inert
# (empty DSN = SDK no-ops) until one is selected and SENTRY_DSN is set.
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float),
        send_default_pii=False,  # NDPA: do not leak PII into error tracking
        environment=config("ENVIRONMENT", default="production"),
    )
