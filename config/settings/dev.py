"""
Development settings for Django project.

This file contains settings specific to local development environments.
It extends the base settings while providing developer-friendly defaults.
"""

import os
import socket
from typing import List

from .base import *  # noqa: F403

# SECURITY CONFIGURATION
# ------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-development-key")
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# DEVELOPMENT TOOLS CONFIGURATION
# ------------------------------------------------------------------------------
# Debug toolbar configuration
INTERNAL_IPS: List[str] = ["127.0.0.1"]

# Add docker host IP to INTERNAL_IPS if running in Docker
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

if DEBUG:
    import mimetypes

    mimetypes.add_type("application/javascript", ".js", True)

    INSTALLED_APPS += ["debug_toolbar"]  # type: ignore
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # type: ignore

# STATIC FILES CONFIGURATION
# ------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# Development-specific middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE,  # Include all middleware from base settings
]

# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
LOGGING["handlers"].update(
    {  # type: ignore
        "process_filename_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_filename.log",  # type: ignore
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "level": "INFO",
        },
        "process_ocr_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_ocr.log",  # type: ignore
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "level": "INFO",
        },
        "process_json_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_json.log",  # type: ignore
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "level": "INFO",
        },
        "process_groq_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "process_groq.log",  # type: ignore
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "level": "INFO",
        },
    }
)

LOGGING["loggers"].update(
    {  # type: ignore
        "main.utils.process_filename": {
            "handlers": ["console", "process_filename_file"],
            "level": "INFO",
            "propagate": False,
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
        "main.utils.process_groq": {
            "handlers": ["console", "process_groq_file"],
            "level": "INFO",
            "propagate": False,
        },
    }
)

# EMAIL CONFIGURATION
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS CONFIGURATION
# ------------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins in development
CORS_URLS_REGEX = r"^/api/.*$"  # Only allow CORS for API endpoints
