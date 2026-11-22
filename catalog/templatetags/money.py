"""Display helpers: cents as dollars, Unix seconds as dates."""

from datetime import UTC, datetime

from django import template

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


register.filter("money", format_cents)
register.filter("unixtime", format_unix)
