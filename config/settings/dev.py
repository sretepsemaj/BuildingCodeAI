"""Development settings for Django project."""

import os
import sys

from .base import ALLOWED_HOSTS, BASE_DIR, DATABASES, DEBUG, INSTALLED_APPS, MIDDLEWARE

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-development-key")

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Debug toolbar settings
if "test" not in sys.argv:  # Don't load debug toolbar during tests
    INSTALLED_APPS += ["debug_toolbar"]  # type: ignore
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # type: ignore

# Internal IPs for debug toolbar
INTERNAL_IPS = [
    "127.0.0.1",
]

# Debug toolbar configuration
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: (
        DEBUG and request.META.get("REMOTE_ADDR", None) in INTERNAL_IPS
    ),
    "IS_RUNNING_TESTS": False,
}

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins in development

# Static files - use whitenoise in development too
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
