"""Development settings. Never used in production — DEBUG is hardcoded True."""
from .base import *  # noqa: F401,F403
from decouple import Csv, config

DEBUG = True

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# Verbose SQL logging locally only — never enable in production (leaks query
# shapes/timings and is a meaningful performance cost under load).
LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
    "handlers": ["console"],
    "level": config("SQL_LOG_LEVEL", default="WARNING"),
    "propagate": False,
}

CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS += ["django_extensions"]  # noqa: F405
