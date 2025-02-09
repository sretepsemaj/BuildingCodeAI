"""Django settings package.

This package contains different settings configurations for various environments.
It automatically loads the appropriate settings based on DJANGO_SETTINGS_MODULE
or falls back to development settings if not specified.
"""

import os
from pathlib import Path

from .base import *  # noqa: F403


# Validate environment setup
def validate_environment():
    """Validate critical environment variables are set."""
    required_settings = {
        "production": [
            "DJANGO_SECRET_KEY",
            "ALLOWED_HOSTS",
            "DATABASE_URL",
        ],
        "staging": [
            "DJANGO_SECRET_KEY",
            "ALLOWED_HOSTS",
            "DATABASE_URL",
        ],
    }

    env = os.getenv("DJANGO_ENV", "development")
    if env in required_settings:
        missing = [var for var in required_settings[env] if not os.getenv(var)]
        if missing:
            raise ValueError(
                f"Missing required environment variables for {env} environment: "
                f"{', '.join(missing)}"
            )


# Determine which settings to use
DJANGO_SETTINGS_MODULE = os.getenv("DJANGO_SETTINGS_MODULE", "")
if DJANGO_SETTINGS_MODULE:
    if DJANGO_SETTINGS_MODULE == "config.settings.prod":
        os.environ["DJANGO_ENV"] = "production"
    elif DJANGO_SETTINGS_MODULE == "config.settings.staging":
        os.environ["DJANGO_ENV"] = "staging"
    elif DJANGO_SETTINGS_MODULE == "config.settings.test":
        os.environ["DJANGO_ENV"] = "test"
else:
    # Default to development settings
    os.environ["DJANGO_ENV"] = "development"

# Validate environment before loading settings
validate_environment()

# Load environment-specific settings
env = os.getenv("DJANGO_ENV")
if env == "production":
    from .prod import *  # noqa: F403
elif env == "staging":
    from .staging import *  # noqa: F403
elif env == "test":
    from .test import *  # noqa: F403
else:
    # Try to load local settings if they exist, otherwise use dev settings
    try:
        from .local import *  # noqa: F403
    except ImportError:
        from .dev import *  # noqa: F403
