"""Product queries. Every filter used by the storefront and the API lives here."""

from django.apps import apps
from django.db import models
from django.db.models import Count, Exists, OuterRef, Q

MAX_SEARCH_WORDS = 10


class ProductQuerySet(models.QuerySet):
    def search(self, text):
        """Every word must appear in the name or the description (case-insensitive)."""
        words = (text or "").split()[:MAX_SEARCH_WORDS]
        query = Q()
        for word in words:
            query &= Q(name__icontains=word) | Q(description__icontains=word)
        return self.filter(query)

    def in_category(self, category_id):
        """Products in the category or any category below it (one `IN` over product-holding ids, no joins)."""
        from catalog.category_tree import get_category_tree

        return self.filter(category_id__in=get_category_tree().product_descendant_ids(category_id))

    def with_tags(self, tag_ids, match="all"):
        """Products with ALL (default) or ANY of the tags.

        Uses a subquery on the many-to-many table, so the outer query never
        joins tags and never needs `.distinct()`.
        """
        tag_ids = list(dict.fromkeys(tag_ids))
        if not tag_ids:
            return self
        through = self.model.tags.through.objects.filter(tag_id__in=tag_ids)
        if match == "all":
            through = (
                through.values("product_id").annotate(n=Count("tag_id")).filter(n=len(tag_ids))
            )
        return self.filter(id__in=through.values("product_id"))

    def price_between(self, min_cents=None, max_cents=None):
        qs = self
        if min_cents is not None:
            qs = qs.filter(price_cents__gte=min_cents)
        if max_cents is not None:
            qs = qs.filter(price_cents__lte=max_cents)
        return qs

    def in_stock(self):
        return self.filter(items_available__gt=0)

    def favorites_of(self, user):
        Favorite = apps.get_model("catalog", "Favorite")
        return self.filter(id__in=Favorite.objects.filter(user=user).values("product_id"))

    def with_is_favorite(self, user):
        """Annotate `is_favorite` for the user (always False for anonymous users)."""
        if not user.is_authenticated:
            return self.annotate(is_favorite=models.Value(False, output_field=models.BooleanField()))
        Favorite = apps.get_model("catalog", "Favorite")
        return self.annotate(
            is_favorite=Exists(Favorite.objects.filter(user=user, product_id=OuterRef("pk")))
        )

    def for_listing(self, user=None):
        """Fixed number of queries per page: products + tags (+ favourites via EXISTS)."""
        qs = self.select_related("category").prefetch_related("tags").order_by("name", "id")
        if user is not None:
            qs = qs.with_is_favorite(user)
        return qs
