"""Clear the cached category tree once a category change commits.

Using `on_commit` means a concurrent request cannot re-cache the old tree
between our save and the commit, and a rolled-back save leaves the cache alone.
"""

from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from catalog.category_tree import CACHE_KEY
from catalog.models import Category


@receiver(post_save, sender=Category, dispatch_uid="catalog.category.saved")
@receiver(post_delete, sender=Category, dispatch_uid="catalog.category.deleted")
def invalidate_category_tree(**kwargs):
    transaction.on_commit(lambda: cache.delete(CACHE_KEY))
