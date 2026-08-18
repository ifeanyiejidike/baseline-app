"""
Celery application entrypoint. Run with:

    celery -A config worker -l info
    celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

Both commands import this module via `-A config`, which is why it lives at
`config/celery.py` rather than inside a specific app.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("baseline")

# Reads every CELERY_* setting from Django settings (namespace="CELERY"
# strips that prefix, so CELERY_BROKER_URL in settings becomes
# app.conf.broker_url here).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discovers a `tasks.py` in every app listed in INSTALLED_APPS —
# apps/invoices/tasks.py and apps/projects/tasks.py are picked up this way,
# with no manual task registration needed.
app.autodiscover_tasks()
