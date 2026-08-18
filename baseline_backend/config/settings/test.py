"""Test settings. Requires a real Postgres instance — RLS policies (the
whole point of the tenant-isolation test suite) are Postgres-specific and
cannot be exercised against sqlite. Point DB_HOST/DB_USER/DB_PASSWORD at a
disposable local or CI Postgres instance."""
from .development import *  # noqa: F401,F403

# Fast, insecure hasher — never use MD5PasswordHasher outside tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DATABASES["default"]["NAME"] = config("TEST_DB_NAME", default="baseline_test")  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# No real broker in tests — tasks execute synchronously, in-process.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
