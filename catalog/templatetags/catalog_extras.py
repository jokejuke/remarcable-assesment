from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from catalog.category_tree import get_category_tree

register = template.Library()


@register.filter
def category_path(category_id):
    """Full path label from the cached tree, e.g. "Electronics > Audio > Headphones"."""
    return get_category_tree().path(category_id)


def _category_input(node_id, name, selected):
    value = "" if node_id is None else str(node_id)
    return format_html(
        '<label><input type="radio" name="category" value="{}" id="id_category_{}"{}> {}</label>',
        value,
        value or "all",
        mark_safe(" checked") if selected else "",
        name,
    )


@register.simple_tag
def category_tree_nav(tree, selected=""):
    """The category filter: "All" plus the tree as nested native `<details>` (no JavaScript needed).

    A branch is open when it contains the selected category. Parents are selectable too; their
    radio sits inside the `<summary>`, so the disclosure arrow only expands.
    """
    selected = str(selected or "")
    selected_id = int(selected) if selected.isdigit() else None
    children = {}
    for node in tree.nodes:
        children.setdefault(node.parent_id, []).append(node)

    def render(parent_id):
        items = []
        for node in children.get(parent_id, []):
            is_selected = str(node.id) == selected
            if node.has_subcategories:
                open_attr = mark_safe(" open") if selected_id in tree.descendant_ids(node.id) else ""
                items.append(
                    format_html(
                        "<li><details{}><summary>{}</summary>{}</details></li>",
                        open_attr,
                        _category_input(node.id, node.name, is_selected),
                        render(node.id),
                    )
                )
            else:
                items.append(format_html("<li>{}</li>", _category_input(node.id, node.name, is_selected)))
        return format_html("<ul>{}</ul>", mark_safe("".join(items))) if items else ""

    return format_html(
        '<div class="category-tree">{}{}</div>', _category_input(None, "All", not selected), render(None)
    )
