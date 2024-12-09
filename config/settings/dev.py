"""
Development settings for Django project.

This file contains settings specific to local development environments.
It extends the base settings while providing developer-friendly defaults.
"""

import os
import socket
from pathlib import Path
from typing import List

from .base import *  # noqa: F403

# CORE CONFIGURATION
# ------------------------------------------------------------------------------
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# DIRECTORY STRUCTURE CONFIGURATION
# ------------------------------------------------------------------------------
# Base directories
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
LOGS_DIR = BASE_DIR / "logs"

# Create base directories
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Plumbing code processing directories
PLUMBING_CODE_BASE_DIR = MEDIA_ROOT / "plumbing_code"
PLUMBING_CODE_DIRS = [
    "uploads",
    "ocr",
    "original",
    "tables",
    "analytics",
    "embeddings",
    "json",
    "json_final",
    "json_processed",
    "optimizer",
    "text",  # Add text directory for OCR output
]

# Create plumbing code directories
PLUMBING_CODE_BASE_DIR.mkdir(parents=True, exist_ok=True)
for dir_name in PLUMBING_CODE_DIRS:
    (PLUMBING_CODE_BASE_DIR / dir_name).mkdir(parents=True, exist_ok=True)

# Create paths dictionary for use in processing
PLUMBING_CODE_PATHS = {dirname: PLUMBING_CODE_BASE_DIR / dirname for dirname in PLUMBING_CODE_DIRS}

# URL CONFIGURATION
# ------------------------------------------------------------------------------
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

# STATIC FILES CONFIGURATION
# ------------------------------------------------------------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
STATICFILES_DIRS = [
    BASE_DIR / "main" / "static",
]

# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "process_ocr_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_ocr.log",
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "level": "INFO",
        },
        "process_json_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_json.log",
            "formatter": "verbose",
            "maxBytes": 10485760,
            "backupCount": 3,
            "level": "INFO",
        },
        "process_start_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_start.log",
            "formatter": "verbose",
            "maxBytes": 10485760,
            "backupCount": 3,
            "level": "INFO",
        },
        "process_filename_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_filename.log",
            "formatter": "verbose",
            "maxBytes": 10485760,
            "backupCount": 3,
            "level": "INFO",
        },
        "process_groq_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_groq.log",
            "formatter": "verbose",
            "maxBytes": 10485760,
            "backupCount": 3,
            "level": "INFO",
        },
        "django_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "django.log",
            "formatter": "verbose",
            "maxBytes": 10485760,
            "backupCount": 3,
            "level": "INFO",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "django_file"],
            "level": "INFO",
            "propagate": True,
        },
        "main.utils.process_ocr": {
            "handlers": ["console", "process_ocr_file"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_json": {
            "handlers": ["console", "process_json_file"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_start": {
            "handlers": ["console", "process_start_file"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_filename": {
            "handlers": ["console", "process_filename_file"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_groq": {
            "handlers": ["console", "process_groq_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# DEBUG TOOLBAR CONFIGURATION
# ------------------------------------------------------------------------------
if DEBUG:
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]

    # Add debug toolbar to installed apps
    INSTALLED_APPS += ["debug_toolbar"]

    # Add debug toolbar middleware at start of middleware list
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
