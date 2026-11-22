"""Small helpers to build test data without fixtures."""

from django.contrib.auth import get_user_model

from catalog.models import Category, Product, Tag


def container(name, parent=None):
    return Category.objects.create(name=name, parent=parent, has_products=False, has_subcategories=True)


def leaf(name, parent=None):
    return Category.objects.create(name=name, parent=parent, has_products=True, has_subcategories=False)


def product(name, category, price_cents=1000, items_available=5, description="", tags=()):
    p = Product.objects.create(
        name=name,
        category=category,
        price_cents=price_cents,
        items_available=items_available,
        description=description,
    )
    if tags:
        p.tags.set(tags)
    return p


def tags(*names):
    return [Tag.objects.create(name=n) for n in names]


def user(username="shopper", password="pass-for-tests-123", **extra):
    return get_user_model().objects.create_user(username=username, password=password, **extra)


def build_tree():
    """Electronics > Audio > {Headphones, Speakers}; Electronics > Computers; Books > Fiction."""
    t = {}
    t["electronics"] = container("Electronics")
    t["audio"] = container("Audio", t["electronics"])
    t["headphones"] = leaf("Headphones", t["audio"])
    t["speakers"] = leaf("Speakers", t["audio"])
    t["computers"] = leaf("Computers", t["electronics"])
    t["books"] = container("Books")
    t["fiction"] = leaf("Fiction", t["books"])
    return t
