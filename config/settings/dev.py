"""Development settings for Django project."""

import os
import socket
import sys

from .base import (
    ALLOWED_HOSTS,
    AWS,
    AWS_RESOURCES,
    BASE_DIR,
    DATABASES,
    DEBUG,
    INSTALLED_APPS,
    MIDDLEWARE,
    STATIC_URL,
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-development-key")

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Static files configuration
STATIC_URL = "/static/"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# Development-specific middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Add whitenoise for static files
    *MIDDLEWARE,  # Include all middleware from base settings
]

# Debug toolbar settings
INTERNAL_IPS = ["127.0.0.1"]

# Add docker host IP to INTERNAL_IPS if running in Docker
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

# Add debug toolbar
if DEBUG:
    import mimetypes

    mimetypes.add_type("application/javascript", ".js", True)

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }

# URL Configuration
ROOT_URLCONF = "config.urls"

# Development-specific logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/debug.log",
            "formatter": "verbose",
        },
        "aws_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs/process_aws.log",
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_aws": {
            "handlers": ["console", "aws_file"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_start": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Development-specific database settings
DATABASES["default"].update(
    {
        "CONN_MAX_AGE": 0,  # Disable persistent connections
        "ATOMIC_REQUESTS": True,  # Wrap each request in a transaction
        "OPTIONS": {
            "timeout": 20,  # 20 second timeout
        },
    }
)

# Development-specific template settings
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
            "debug": DEBUG,
        },
    }
]

# Development-specific email settings
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins in development
CORS_URLS_REGEX = r"^/api/.*$"  # Only allow CORS for API endpoints
