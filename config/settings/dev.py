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
    LOGGING,
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

# Ensure logs directory exists
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Development-specific logging
DEV_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
        },
        "filename_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_filename.log",
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "level": "INFO",
        },
        "ocr_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_ocr.log",
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "level": "INFO",
        },
        "json_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_json.log",
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "level": "INFO",
        },
        "process_json_file": {
            "class": "logging.FileHandler",
            "filename": str(BASE_DIR / "logs" / "process_json.log"),
            "formatter": "verbose",
        },
        "process_groq_file": {
            "class": "logging.FileHandler",
            "filename": str(BASE_DIR / "logs" / "process_groq.log"),
            "formatter": "verbose",
        },
    },
    "loggers": {
        "main.utils.process_filename": {
            "handlers": ["console", "filename_file"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_ocr": {
            "handlers": ["console", "ocr_file"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_json": {
            "handlers": ["console", "process_json_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "main.utils.process_groq": {
            "handlers": ["console", "process_groq_file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

# Use the development logging configuration
LOGGING = DEV_LOGGING

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
