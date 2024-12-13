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
from .paths import MEDIA_ROOT, PLUMBING_CODE_DIR, PLUMBING_CODE_PATHS

# CORE CONFIGURATION
# ------------------------------------------------------------------------------
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# DIRECTORY STRUCTURE CONFIGURATION
# ------------------------------------------------------------------------------
# Base directories
STATIC_ROOT = BASE_DIR / "staticfiles"
LOGS_DIR = BASE_DIR / "logs"

# Create base directories
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------
MEDIA_ROOT = MEDIA_ROOT
MEDIA_ROOT.mkdir(exist_ok=True)

# PLUMBING CODE CONFIGURATION
# ------------------------------------------------------------------------------
PLUMBING_CODE_DIR = PLUMBING_CODE_DIR
PLUMBING_CODE_PATHS = PLUMBING_CODE_PATHS

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
# Get base logging config
LOGGING = LOGGING.copy()  # type: ignore

# Add file handlers
LOGGING["handlers"].update(
    {
        "process_ocr": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "process_ocr.log"),
            "formatter": "verbose",
            "mode": "w",  # Overwrite mode
        },
        "process_filename": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "process_filename.log"),
            "formatter": "verbose",
            "mode": "w",  # Overwrite mode
        },
        "process_image": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "process_image.log"),
            "formatter": "verbose",
            "mode": "w",  # Overwrite mode
        },
        "images_optimizer": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "images_optimizer.log"),
            "formatter": "verbose",
            "mode": "w",  # Overwrite mode
        },
        "process_json": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "process_json.log"),
            "formatter": "verbose",
            "mode": "w",  # Overwrite mode
        },
        "process_json_wash": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "process_json_wash.log"),
            "formatter": "verbose",
            "mode": "w",  # Overwrite mode
        },
        "process_groq": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "process_groq.log"),
            "formatter": "verbose",
            "mode": "w",  # Overwrite mode
        },
        "process_aws": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "process_aws.log"),
            "formatter": "verbose",
            "mode": "w",  # Overwrite mode
        },
        "django": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "django.log"),
            "formatter": "verbose",
            "mode": "w",  # Overwrite mode
        },
    }
)

# Update loggers configuration
LOGGING["loggers"].update(
    {
        "main.utils.process_ocr": {
            "handlers": ["console", "process_ocr"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_filename": {
            "handlers": ["console", "process_filename"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_image": {
            "handlers": ["console", "process_image"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.images_optimizer": {
            "handlers": ["console", "images_optimizer"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_json": {
            "handlers": ["console", "process_json"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_json_wash": {
            "handlers": ["console", "process_json_wash"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_groq": {
            "handlers": ["console", "process_groq"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.process_aws": {
            "handlers": ["console", "process_aws"],
            "level": "INFO",
            "propagate": False,
        },
        "django": {
            "handlers": ["console", "django"],
            "level": "INFO",
            "propagate": False,
        },
    }
)

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
