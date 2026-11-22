"""Catalog data model: a category tree, products, tags, favourites and orders."""

import time

from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import models

from .querysets import ProductQuerySet


def unix_now():
    """Current time as whole Unix seconds."""
    return int(time.time())


class TimestampedModel(models.Model):
    """Adds `created_at` / `updated_at` as Unix seconds.

    `save()` refreshes `updated_at`. Code that writes through `QuerySet.update()`
    must set `updated_at` itself (see `services.place_order`).
    """

    created_at = models.PositiveBigIntegerField(default=unix_now, editable=False)
    updated_at = models.PositiveBigIntegerField(default=unix_now, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.updated_at = unix_now()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "updated_at"}
        super().save(*args, **kwargs)


class Category(TimestampedModel):
    """A node in the category tree.

    A category holds either products or subcategories (exactly one flag is
    True). Rules that span several rows (loops, depth, parent kind) are checked
    in `clean()`; the admin is the only write path, and a test validates the
    fixtures, which skip `clean()`.
    """

    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
        limit_choices_to={"has_subcategories": True},
    )
    has_products = models.BooleanField(default=True)
    has_subcategories = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(has_products=True, has_subcategories=False)
                    | models.Q(has_products=False, has_subcategories=True)
                ),
                name="category_holds_exactly_one_kind",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def path(self):
        from .category_tree import get_category_tree

        return get_category_tree().path(self.pk) if self.pk else self.name

    def clean(self):
        super().clean()
        if self.has_products == self.has_subcategories:
            raise ValidationError("A category must hold either products or subcategories, not both or neither.")

        max_depth = settings.CATALOG_MAX_CATEGORY_DEPTH
        # Always read the tree from the database, never from the cache.
        parents = dict(Category.objects.values_list("id", "parent_id"))
        if self.pk is not None:
            parents[self.pk] = self.parent_id

        errors = {}

        # Loops: walk up from the new parent; reaching self means a cycle.
        if self.parent_id is not None:
            seen = set()
            node = self.parent_id
            while node is not None:
                if node == self.pk or node in seen:
                    raise ValidationError({"parent": "A category cannot be placed under itself or its own descendant."})
                seen.add(node)
                node = parents.get(node)

        depth = self._depth(self.parent_id, parents) + 1
        if depth > max_depth:
            errors["parent"] = f"The tree cannot be deeper than {max_depth} levels; this category would be at level {depth}."
        elif self.pk is not None:
            subtree = self._subtree_height(self.pk, parents)
            if depth + subtree > max_depth:
                errors["parent"] = (
                    f"Moving here would put its subcategories at level {depth + subtree}; the maximum is {max_depth}."
                )

        if self.parent_id is not None:
            parent = Category.objects.filter(pk=self.parent_id).values("has_subcategories").first()
            if parent is not None and not parent["has_subcategories"]:
                errors.setdefault("parent", "The parent must be a category that holds subcategories.")

        if depth >= max_depth and self.has_subcategories:
            errors[NON_FIELD_ERRORS] = f"Categories at level {max_depth} (the deepest level) must hold products."

        if self.pk is not None:
            # Kind errors are non-field: the admin edits both flags through one "kind" field.
            if self.has_subcategories and self.products.exists():
                errors[NON_FIELD_ERRORS] = "This category has products, so it cannot be switched to hold subcategories."
            if self.has_products and self.children.exists():
                errors[NON_FIELD_ERRORS] = "This category has subcategories, so it cannot be switched to hold products."

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def _depth(node_id, parents):
        """Number of levels from the top down to and including `node_id` (0 for None)."""
        depth = 0
        seen = set()
        while node_id is not None and node_id not in seen:
            seen.add(node_id)
            depth += 1
            node_id = parents.get(node_id)
        return depth

    @staticmethod
    def _subtree_height(node_id, parents):
        """Levels below `node_id` (0 for a category without children)."""
        children = {}
        for child, parent in parents.items():
            children.setdefault(parent, []).append(child)
        height, frontier = 0, [node_id]
        while True:
            frontier = [c for n in frontier for c in children.get(n, []) if c != node_id]
            if not frontier:
                return height
            height += 1


class Tag(TimestampedModel):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(TimestampedModel):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    price_cents = models.PositiveIntegerField(help_text="Price in cents, e.g. 4900 for $49.00.")
    items_available = models.PositiveIntegerField(default=0, help_text="Units in stock.")
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        limit_choices_to={"has_products": True},
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(price_cents__gte=0), name="product_price_non_negative"),
            models.CheckConstraint(condition=models.Q(items_available__gte=0), name="product_stock_non_negative"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.category_id is not None:
            holds_products = Category.objects.filter(pk=self.category_id).values_list("has_products", flat=True).first()
            if holds_products is False:
                raise ValidationError({"category": "Products can only be placed in a category that holds products."})


class Favorite(TimestampedModel):
    """A product a user marked as a favourite (at most once per pair)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="favorite_unique_user_product")]

    def __str__(self):
        return f"{self.user} ♥ {self.product}"


class Order(TimestampedModel):
    """A placed order. Prices are copied at purchase, so repricing never changes it."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    total_cents = models.PositiveIntegerField()

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Order #{self.pk}"


class OrderItem(TimestampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    unit_price_cents = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="order_item_quantity_positive"),
            models.UniqueConstraint(fields=["order", "product"], name="order_item_unique_product"),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product}"

    @property
    def line_total_cents(self):
        return self.quantity * self.unit_price_cents
