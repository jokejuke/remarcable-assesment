"""Display helpers: cents as dollars, Unix seconds as dates."""

from datetime import UTC, datetime

from django import template
from django.utils.html import format_html

register = template.Library()


def format_cents(cents):
    """4900 -> "$49.00"."""
    if cents is None:
        return ""
    cents = int(cents)
    sign = "-" if cents < 0 else ""
    dollars, rest = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{rest:02d}"


def format_unix(seconds):
    """1700000000 -> "2023-11-14 22:13 UTC"."""
    if seconds is None:
        return ""
    return datetime.fromtimestamp(int(seconds), tz=UTC).strftime("%Y-%m-%d %H:%M UTC")


def unix_time_element(seconds):
    """1700000000 -> a `<time>` with the UTC instant and UTC fallback text.

    The base template's script rewrites the text into the viewer's local time zone; without
    JavaScript the UTC text stays.
    """
    if seconds is None:
        return ""
    instant = datetime.fromtimestamp(int(seconds), tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return format_html('<time class="local-time" datetime="{}">{}</time>', instant, format_unix(seconds))


register.filter("money", format_cents)
register.filter("unixtime", unix_time_element)
