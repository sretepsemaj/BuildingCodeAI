"""Django settings package.

This package contains different settings configurations for development and production.
"""

import os

# Import all settings from base.py
from .base import *  # noqa: F403

# Load environment-specific settings
if os.environ.get("DJANGO_ENV") == "production":
    from .prod import *  # noqa: F403
else:
    from .dev import *  # noqa: F403
