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
    has_subcategories: bool


class CategoryTree:
    """Ordered nodes, full path labels and descendant lookups.

    The examples in the docstrings below all use this sample, as `rows`
    of (id, parent_id, name, has_products, has_subcategories):

        (1, None, "Electronics", False, True)
        (2, 1,    "Audio",       False, True)
        (3, 2,    "Headphones",  True,  False)
        (4, 1,    "Cameras",     True,  False)
        (5, None, "Books",       True,  False)

    i.e. Books and Electronics at the top; Electronics holds Audio (holding Headphones) and Cameras.
    """

    def __init__(self, rows):
        """Index `rows` once so every later lookup is a dict read.

        by_id    = {1: (None, "Electronics", False, True), 2: (1, "Audio", False, True), ...}
        children = {None: [5, 1], 1: [2, 4], 2: [3]}   # parent_id -> child ids, sorted by lower-case name

        `visit(node_id, prefix)` walks the tree depth-first and returns the set of ids in
        that node's subtree, which its parent merges into its own. For the sample:

            visit(5, "")                           -> {5}
            visit(1, "")                           -> {1, 2, 3, 4}
              visit(2, "Electronics")              -> {2, 3}
                visit(3, "Electronics > Audio")    -> {3}
              visit(4, "Electronics")              -> {4}

        Every visit also records its results, giving (for the sample):

            nodes               = (Books, Electronics, Audio, Headphones, Cameras)
            paths[3]            = "Electronics > Audio > Headphones"
            descendants[1]      = {1, 2, 3, 4}
            product_descendants = {1: {3, 4}, 2: {3}, 3: {3}, 4: {4}, 5: {5}}   # only has_products nodes
        """
        by_id, children = {}, {}
        for id_, parent_id, name, has_products, has_subcategories in rows:
            by_id[id_] = (parent_id, name, has_products, has_subcategories)
            children.setdefault(parent_id, []).append(id_)
        for ids in children.values():
            ids.sort(key=lambda i: by_id[i][1].lower())

        nodes, paths, descendants, product_descendants = [], {}, {}, {}

        def visit(node_id, prefix):
            parent_id, name, has_products, has_subcategories = by_id[node_id]
            label = f"{prefix} > {name}" if prefix else name
            nodes.append(CategoryNode(node_id, parent_id, name, has_subcategories))
            paths[node_id] = label
            subtree = {node_id}
            for child in children.get(node_id, []):
                subtree |= visit(child, label)
            descendants[node_id] = frozenset(subtree)
            product_descendants[node_id] = frozenset(i for i in subtree if by_id[i][2])
            return subtree

        for root in children.get(None, []):
            visit(root, "")

        self._nodes = tuple(nodes)
        self._paths = paths
        self._descendants = descendants
        self._product_descendants = product_descendants

    @property
    def nodes(self):
        """All categories in depth-first order, siblings sorted by name.

        Sample -> names (Books, Electronics, Audio, Headphones, Cameras)
        """
        return self._nodes

    def path(self, category_id):
        """Full label, or "" for an unknown id.

        Sample: path(3) -> "Electronics > Audio > Headphones", path(5) -> "Books", path(99) -> ""
        """
        return self._paths.get(category_id, "")

    def descendant_ids(self, category_id):
        """Ids of the category and every category below it (empty for an unknown id).

        Sample: descendant_ids(1) -> frozenset({1, 2, 3, 4}), descendant_ids(3) -> frozenset({3}),
        descendant_ids(99) -> frozenset()
        """
        return self._descendants.get(category_id, frozenset())

    def product_descendant_ids(self, category_id):
        """Ids of the category and every category below it that can hold products (`has_products`).

        Sample: product_descendant_ids(1) -> frozenset({3, 4}) (1 and 2 only contain subcategories),
        product_descendant_ids(2) -> frozenset({3}), product_descendant_ids(99) -> frozenset()
        """
        return self._product_descendants.get(category_id, frozenset())


def get_category_tree():
    """The cached tree; the first call (or the first after `signals.py` cleared it) runs one query."""
    from catalog.models import Category

    return cache.get_or_set(
        CACHE_KEY,
        lambda: CategoryTree(
            list(Category.objects.order_by().values_list("id", "parent_id", "name", "has_products", "has_subcategories"))
        ),
        timeout=CACHE_TIMEOUT,
    )
