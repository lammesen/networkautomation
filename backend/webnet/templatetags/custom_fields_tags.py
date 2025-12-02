"""Template tags for custom fields."""

from django import template
import json

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def is_safe_url(url):
    """Check if a URL has a safe scheme (http/https)."""
    if not url:
        return False
    url_lower = str(url).lower().strip()
    return url_lower.startswith("http://") or url_lower.startswith("https://")


@register.filter
def json_pretty(value):
    """Format JSON data for safe display."""
    if value is None:
        return ""
    try:
        if isinstance(value, str):
            # Try to parse if it's a JSON string
            value = json.loads(value)
        return json.dumps(value, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return str(value)
