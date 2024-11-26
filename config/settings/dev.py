"""Development settings."""
from .base import *
import sys
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-development-key')

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Debug toolbar settings
if not 'test' in sys.argv:  # Don't load debug toolbar during tests
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

# Internal IPs for debug toolbar
INTERNAL_IPS = [
    '127.0.0.1',
]

# Debug toolbar configuration
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG and request.META.get('REMOTE_ADDR', None) in INTERNAL_IPS,
    'IS_RUNNING_TESTS': False,
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins in development

# Static files - use whitenoise in development too
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

OPEN_API_KEY = os.getenv('OPEN_API_KEY')  # Use the same key for MYSK
PLEX_API_KEY = os.getenv('PLEX_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
HUGG_API_KEY = os.getenv('HUGG_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
PINE_API_KEY = os.getenv('PINE_API_KEY')
TUBE_API_KEY = os.getenv('TUBE_API_KEY')
LAMA_API_KEY = os.getenv('LAMA_API_KEY')

# API URLs
HUGG_API_URL = os.getenv('HUGG_API_URL')
PLEX_API_URL = os.getenv('PLEX_API_URL')
PINE_ENVIRONMENT = os.getenv('PINE_ENVIRONMENT')
