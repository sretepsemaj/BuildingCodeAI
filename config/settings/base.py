"""
Django settings for config project.

This is the base settings file containing all common settings across environments.
Environment-specific settings should go in their respective files (dev.py, prod.py).
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv


# ENVIRONMENT CONFIGURATION
# ------------------------------------------------------------------------------
def get_env_value(env_variable: str, default: Any = None, required: bool = False) -> Any:
    """Get an environment variable or return its default."""
    value = os.getenv(env_variable)
    if value is None and required:
        raise ImproperlyConfigured(f"Environment variable {env_variable} is required.")
    return value if value is not None else default


def get_bool_env(env_variable: str, default: bool = False) -> bool:
    """Get a boolean environment variable."""
    value = get_env_value(env_variable, default=str(default))
    return value.lower() in ("true", "t", "1", "yes", "y")


def get_int_env(env_variable: str, default: int = 0) -> int:
    """Get an integer environment variable."""
    value = get_env_value(env_variable, default=default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_list_env(
    env_variable: str, default: Optional[List[str]] = None, separator: str = ","
) -> List[str]:
    """Get a list from an environment variable."""
    if default is None:
        default = []
    value = get_env_value(env_variable)
    if value is None:
        return default
    return [item.strip() for item in value.split(separator)]


# Load environment variables
load_dotenv()

# CORE CONFIGURATION
# ------------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
DEBUG: bool = False
ROOT_URLCONF: str = "config.urls"
WSGI_APPLICATION: str = "config.wsgi.application"

# APPLICATION CONFIGURATION
# ------------------------------------------------------------------------------
DJANGO_APPS: List[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS: List[str] = [
    "corsheaders",
]

LOCAL_APPS: List[str] = [
    "main",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------
MIDDLEWARE: List[str] = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# SECURITY CONFIGURATION
# ------------------------------------------------------------------------------
def generate_secret_key() -> None:
    """Generate a secure secret key."""
    if not os.path.exists(".env"):
        with open(".env", "a") as f:
            f.write(f'SECRET_KEY="{get_random_secret_key()}"\n')


def get_secret_key() -> str:
    """Get or generate the secret key."""
    secret_key = get_env_value("SECRET_KEY")
    if not secret_key:
        generate_secret_key()
        secret_key = get_env_value("SECRET_KEY")
    return str(secret_key)


SECRET_KEY: str = get_secret_key()
ALLOWED_HOSTS: List[str] = []

# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "media/"

# STATIC FILES CONFIGURATION
# ------------------------------------------------------------------------------
STATIC_URL: str = "static/"
STATICFILES_DIRS: List[Path] = []

# TEMPLATES CONFIGURATION
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # Let each environment specify template dirs
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# INTERNATIONALIZATION CONFIGURATION
# ------------------------------------------------------------------------------
LANGUAGE_CODE: str = "en-us"
TIME_ZONE: str = "America/New_York"
USE_I18N: bool = True
USE_TZ: bool = True
