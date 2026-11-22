"""Clear the cached category tree once a category change commits.

Using `on_commit` means a concurrent request cannot re-cache the old tree
between our save and the commit, and a rolled-back save leaves the cache alone.
"""

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .category_tree import clear_category_tree_cache
from .models import Category


@receiver(post_save, sender=Category, dispatch_uid="catalog.category.saved")
@receiver(post_delete, sender=Category, dispatch_uid="catalog.category.deleted")
def invalidate_category_tree(sender, **kwargs):
    transaction.on_commit(clear_category_tree_cache)
