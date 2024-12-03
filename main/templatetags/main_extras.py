from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def get_media_url(path):
    """Convert a relative media path to a full URL."""
    if path.startswith("/"):
        path = path[1:]
    return f"{settings.MEDIA_URL}{path}"
