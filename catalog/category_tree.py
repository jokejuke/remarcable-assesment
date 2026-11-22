"""Cached, immutable view of the category tree.

Built from one query and stored in the cache. `signals.py` clears the cache
after any category save or delete commits; the timeout is a safety net for
writes that bypass signals (`QuerySet.update()` / `bulk_create()` on
categories, which the code never does).
"""

from dataclasses import dataclass

from django.core.cache import cache

CACHE_KEY = "catalog:category-tree:v1"
CACHE_TIMEOUT = 60 * 60  # 1 hour


@dataclass(frozen=True)
class CategoryNode:
    id: int
    parent_id: int | None
    name: str
    has_products: bool
    has_subcategories: bool
    depth: int  # 1 for top-level categories


class CategoryTree:
    """Ordered nodes, full path labels and descendant lookups."""

    def __init__(self, rows):
        by_id = {}
        children = {}
        for id_, parent_id, name, has_products, has_subcategories in rows:
            by_id[id_] = (parent_id, name, has_products, has_subcategories)
            children.setdefault(parent_id, []).append(id_)
        for ids in children.values():
            ids.sort(key=lambda i: by_id[i][1].lower())

        nodes, paths, descendants = [], {}, {}

        def visit(node_id, depth, prefix):
            parent_id, name, has_products, has_subcategories = by_id[node_id]
            label = f"{prefix} > {name}" if prefix else name
            nodes.append(CategoryNode(node_id, parent_id, name, has_products, has_subcategories, depth))
            paths[node_id] = label
            subtree = {node_id}
            for child in children.get(node_id, []):
                subtree |= visit(child, depth + 1, label)
            descendants[node_id] = frozenset(subtree)
            return subtree

        for root in children.get(None, []):
            visit(root, 1, "")

        self._nodes = tuple(nodes)
        self._paths = paths
        self._descendants = descendants

    @property
    def nodes(self):
        """All categories in depth-first order, siblings sorted by name."""
        return self._nodes

    def __contains__(self, category_id):
        return category_id in self._paths

    def path(self, category_id):
        """Full label, e.g. "Electronics > Audio > Headphones"."""
        return self._paths.get(category_id, "")

    def descendant_ids(self, category_id):
        """Ids of the category and every category below it."""
        return self._descendants.get(category_id, frozenset())


def build_category_tree():
    from .models import Category

    rows = Category.objects.order_by().values_list("id", "parent_id", "name", "has_products", "has_subcategories")
    return CategoryTree(list(rows))


def get_category_tree():
    return cache.get_or_set(CACHE_KEY, build_category_tree, timeout=CACHE_TIMEOUT)


def clear_category_tree_cache():
    cache.delete(CACHE_KEY)
