from django import template

from catalog.category_tree import get_category_tree

register = template.Library()


@register.filter
def category_path(category_id):
    """Full path label from the cached tree, e.g. "Electronics > Audio > Headphones"."""
    return get_category_tree().path(category_id)
