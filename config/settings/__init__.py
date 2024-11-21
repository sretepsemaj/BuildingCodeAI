"""Settings package initialization."""
import os
from .base import *

# Load environment-specific settings
DJANGO_ENV = os.getenv('DJANGO_ENV', 'development')

if DJANGO_ENV == 'production':
    from .prod import *
else:
    from .dev import *