"""Spec: demo-data (fixtures)."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from catalog.category_tree import get_category_tree
from catalog.models import Category, Favorite, Product, Tag


class CatalogFixtureOnlyTests(TestCase):
    fixtures = ["catalog"]

    def test_counts(self):
        self.assertGreaterEqual(Category.objects.count(), 5)
        self.assertGreaterEqual(Tag.objects.count(), 10)
        self.assertGreaterEqual(Product.objects.count(), 20)

    def test_creates_no_users(self):
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_three_level_tree_with_products(self):
        cache.clear()
        tree = get_category_tree()
        level3 = [n.id for n in tree.nodes if n.depth == 3]
        self.assertTrue(Product.objects.filter(category_id__in=level3).exists())

    def test_out_of_stock_sample_hidden_by_default(self):
        self.assertTrue(Product.objects.filter(items_available=0).exists())
        response = self.client.get(reverse("catalog:product-list"))
        self.assertLess(response.context["paginator"].count, Product.objects.count())

    def test_products_have_several_tags_and_a_price_range(self):
        self.assertTrue(all(len(p.tags.all()) >= 2 for p in Product.objects.prefetch_related("tags")))
        prices = Product.objects.values_list("price_cents", flat=True)
        self.assertGreater(max(prices), 100 * min(prices))


class FixtureValidationTests(TestCase):
    fixtures = ["catalog", "demo_users"]

    def test_every_record_passes_full_clean(self):
        """`loaddata` skips model validation, so check every rule here."""
        for model in (Category, Tag, Product, Favorite):
            for obj in model.objects.all():
                with self.subTest(model=model.__name__, pk=obj.pk):
                    obj.full_clean()
        for user in get_user_model().objects.all():
            with self.subTest(user=user.username):
                user.full_clean()

    def test_passwords_are_hashes(self):
        for user in get_user_model().objects.all():
            self.assertTrue(user.password.startswith("pbkdf2_sha256$"))

    def test_admin_can_manage_catalog(self):
        self.assertTrue(self.client.login(username="admin", password="demo-admin-123"))
        for url in ("admin:index", "admin:catalog_category_changelist", "admin:catalog_tag_changelist",
                    "admin:catalog_product_changelist", "admin:catalog_product_add"):
            self.assertEqual(self.client.get(reverse(url)).status_code, 200, url)

    def test_shopper_has_no_admin_access(self):
        self.assertTrue(self.client.login(username="shopper", password="demo-shopper-123"))
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(response, f"{reverse('admin:login')}?next={reverse('admin:index')}")

    def test_shopper_has_favourites(self):
        self.assertTrue(self.client.login(username="shopper", password="demo-shopper-123"))
        response = self.client.get(reverse("catalog:my-favorites"))
        self.assertGreaterEqual(len(response.context["products"]), 2)
