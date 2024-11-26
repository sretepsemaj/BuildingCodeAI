import os
from typing import Any, Dict

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def media_url(file_path: str) -> str:
    """
    Convert a file path to a media URL.

    Args:
        file_path (str): The file path to convert.

    Returns:
        str: The media URL for the file.
    """
    if file_path.startswith(settings.MEDIA_ROOT):
        file_path = file_path[len(settings.MEDIA_ROOT)].lstrip(os.sep)

    # Ensure the path starts with MEDIA_URL
    return os.path.join(settings.MEDIA_URL, file_path)


@register.filter(name="get_item")
def get_item(dictionary: Dict[str, Any], key: str) -> Any:
    """Get an item from a dictionary."""
    return dictionary.get(key)
