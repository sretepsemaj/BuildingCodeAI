import os

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def get_media_url(file_path):
    """Convert a file path to a media URL."""
    if not file_path:
        return ""

    # Remove media root from path if present
    if file_path.startswith(settings.MEDIA_ROOT):
        file_path = file_path[len(settings.MEDIA_ROOT) :].lstrip(os.sep)

    # Ensure the path starts with MEDIA_URL
    return os.path.join(settings.MEDIA_URL, file_path)
