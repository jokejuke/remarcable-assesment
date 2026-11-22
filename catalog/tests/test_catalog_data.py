"""Spec: catalog-data (products, tags, admin, display helpers)."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from catalog.models import Product, Tag
from catalog.templatetags.money import format_cents, format_unix

from .factories import build_tree, product, tags


class ProductAndTagModelTests(TestCase):
    def setUp(self):
        self.t = build_tree()

    def test_product_attributes(self):
        wireless, budget = tags("wireless", "budget")
        p = product("Buds", self.t["headphones"], price_cents=4900, items_available=5,
                    description="Small", tags=[wireless, budget])
        p.refresh_from_db()
        self.assertEqual((p.price_cents, p.items_available, p.category, p.description), (4900, 5, self.t["headphones"], "Small"))
        self.assertEqual(set(p.tags.values_list("name", flat=True)), {"wireless", "budget"})

    def test_duplicate_product_name(self):
        product("Buds", self.t["headphones"])
        with self.assertRaises(IntegrityError):
            product("Buds", self.t["speakers"])

    def test_duplicate_tag_name(self):
        tags("wireless")
        with self.assertRaises(IntegrityError):
            tags("wireless")

    def test_generated_slug(self):
        p = product("Aurora ANC Headphones", self.t["headphones"])
        self.assertEqual(p.slug, "aurora-anc-headphones")

    def test_colliding_slug_gets_suffix(self):
        product("C Primer", self.t["fiction"])
        self.assertEqual(product("C++ Primer", self.t["fiction"]).slug, "c-primer-2")
        self.assertEqual(product("C Primer!", self.t["fiction"]).slug, "c-primer-3")

    def test_slug_fallback_for_unsluggable_name(self):
        self.assertEqual(product("!!!", self.t["fiction"]).slug, "product")
        self.assertEqual(product("???", self.t["fiction"]).slug, "product-2")

    def test_rename_keeps_slug(self):
        p = product("Aurora ANC Headphones", self.t["headphones"])
        p.name = "Aurora ANC Headphones II"
        p.save()
        p.refresh_from_db()
        self.assertEqual(p.slug, "aurora-anc-headphones")

    def test_duplicate_hand_set_slug_rejected(self):
        product("Buds", self.t["headphones"])
        other = Product(name="Other", price_cents=1, category=self.t["headphones"], slug="buds")
        with self.assertRaises(ValidationError) as ctx:
            other.full_clean()
        self.assertIn("slug", ctx.exception.message_dict)

    def test_picture_must_be_http_url(self):
        for bad in ("javascript:alert(1)", "ftp://example.com/a.png", "not a url"):
            p = Product(name="X", price_cents=1, category=self.t["headphones"], image_url=bad)
            with self.assertRaises(ValidationError) as ctx:
                p.full_clean()
            self.assertIn("image_url", ctx.exception.message_dict, bad)

    def test_picture_is_optional_and_accepts_https(self):
        for good in ("", "https://upload.wikimedia.org/a.jpg", "http://example.com/a.png"):
            Product(name="X", price_cents=1, category=self.t["headphones"], image_url=good).full_clean()

    def test_negative_price_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            product("Bad", self.t["headphones"], price_cents=-1)

    def test_negative_stock_rejected(self):
        p = product("Buds", self.t["headphones"], items_available=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=p.pk).update(items_available=-1)

    def test_product_edit_changes_updated_at_only(self):
        p = product("Buds", self.t["headphones"])
        Product.objects.filter(pk=p.pk).update(created_at=1000, updated_at=1000)
        p.refresh_from_db()
        with mock.patch("catalog.models.unix_now", return_value=2000):
            p.price_cents = 5900
            p.save()
        p.refresh_from_db()
        self.assertEqual((p.created_at, p.updated_at), (1000, 2000))

    def test_tag_edit_changes_updated_at_only(self):
        (tag,) = tags("wireless")
        Tag.objects.filter(pk=tag.pk).update(created_at=1000, updated_at=1000)
        tag.refresh_from_db()
        with mock.patch("catalog.models.unix_now", return_value=2000):
            tag.name = "bluetooth"
            tag.save()
        tag.refresh_from_db()
        self.assertEqual((tag.created_at, tag.updated_at), (1000, 2000))

    def test_deleting_tag_keeps_products(self):
        (budget,) = tags("budget")
        p = product("Buds", self.t["headphones"], tags=[budget])
        budget.delete()
        self.assertTrue(Product.objects.filter(pk=p.pk).exists())
        self.assertEqual(p.tags.count(), 0)

    def test_category_must_hold_products(self):
        p = Product(name="X", price_cents=1, items_available=1, category=self.t["electronics"])
        with self.assertRaises(ValidationError) as ctx:
            p.full_clean()
        self.assertIn("category", ctx.exception.message_dict)


class DisplayHelperTests(SimpleTestCase):
    def test_money(self):
        self.assertEqual(format_cents(4900), "$49.00")
        self.assertEqual(format_cents(0), "$0.00")
        self.assertEqual(format_cents(5), "$0.05")
        self.assertEqual(format_cents(123456789), "$1,234,567.89")
        self.assertEqual(format_cents(None), "")

    def test_unixtime(self):
        self.assertEqual(format_unix(0), "1970-01-01 00:00 UTC")
        self.assertEqual(format_unix(1700000000), "2023-11-14 22:13 UTC")
        self.assertEqual(format_unix(4102444800), "2100-01-01 00:00 UTC")
        self.assertEqual(format_unix(None), "")


class ProductAdminTests(TestCase):
    def setUp(self):
        self.t = build_tree()
        self.tags = tags("wireless", "budget")
        admin = get_user_model().objects.create_superuser("admin", "a@example.com", "pass-for-tests-123")
        self.client.force_login(admin)

    def _changelist_queries(self, n):
        Product.objects.all().delete()
        for i in range(n):
            product(f"P{i:02d}", self.t["headphones"] if i % 2 else self.t["computers"], tags=self.tags)
        url = reverse("admin:catalog_product_changelist")
        self.client.get(url)  # warm caches (session, category tree, content types)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(ctx.captured_queries)

    def test_changelist_query_count_is_constant(self):
        self.assertEqual(self._changelist_queries(5), self._changelist_queries(20))

    def test_changelist_shows_columns(self):
        product("Buds", self.t["headphones"], price_cents=4900, items_available=7)
        response = self.client.get(reverse("admin:catalog_product_changelist"))
        self.assertContains(response, "Electronics &gt; Audio &gt; Headphones")
        self.assertContains(response, "$49.00")

    def test_changelist_search_and_filters(self):
        product("Buds", self.t["headphones"], tags=[self.tags[0]])
        product("Laptop", self.t["computers"])
        url = reverse("admin:catalog_product_changelist")
        self.assertContains(self.client.get(url, {"q": "Buds"}), "Buds")
        self.assertNotContains(self.client.get(url, {"q": "Buds"}), "Laptop")
        self.assertNotContains(self.client.get(url, {"category__id__exact": self.t["headphones"].pk}), "Laptop")
        self.assertNotContains(self.client.get(url, {"tags__id__exact": self.tags[0].pk}), "Laptop")

    def test_category_choices_only_hold_products(self):
        response = self.client.get(reverse("admin:catalog_product_add"))
        choices = set(response.context["adminform"].form.fields["category"].queryset)
        self.assertEqual(choices, {self.t["headphones"], self.t["speakers"], self.t["computers"], self.t["fiction"]})

    def test_admin_creates_product(self):
        response = self.client.post(
            reverse("admin:catalog_product_add"),
            {
                "name": "Buds", "description": "d", "price_cents": 4900, "items_available": 5,
                "category": self.t["headphones"].pk, "tags": [t.pk for t in self.tags],
            },
        )
        self.assertEqual(response.status_code, 302)
        p = Product.objects.get(name="Buds")
        self.assertEqual(p.tags.count(), 2)

    def test_admin_forms_show_slug_and_picture(self):
        for url in (
            reverse("admin:catalog_product_add"),
            reverse("admin:catalog_product_change", args=[product("Buds", self.t["headphones"]).pk]),
        ):
            form = self.client.get(url).context["adminform"].form
            self.assertIn("slug", form.fields)
            self.assertIn("image_url", form.fields)
        self.assertContains(self.client.get(reverse("admin:catalog_product_add")), "data-prepopulated-fields")

    def test_admin_creates_product_with_picture_and_slug(self):
        response = self.client.post(
            reverse("admin:catalog_product_add"),
            {
                "name": "Buds", "slug": "my-buds", "image_url": "https://example.com/b.jpg", "description": "d",
                "price_cents": 4900, "items_available": 5, "category": self.t["headphones"].pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        p = Product.objects.get(name="Buds")
        self.assertEqual((p.slug, p.image_url), ("my-buds", "https://example.com/b.jpg"))

    def test_admin_rejects_javascript_picture(self):
        response = self.client.post(
            reverse("admin:catalog_product_add"),
            {"name": "Buds", "image_url": "javascript:alert(1)", "price_cents": 1, "items_available": 1,
             "category": self.t["headphones"].pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("image_url", response.context["adminform"].form.errors)

    def test_admin_rejects_subcategory_holding_category(self):
        response = self.client.post(
            reverse("admin:catalog_product_add"),
            {"name": "Bad", "price_cents": 1, "items_available": 1, "category": self.t["electronics"].pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["adminform"].form.errors)

    def test_tag_changelist(self):
        self.assertEqual(self.client.get(reverse("admin:catalog_tag_changelist")).status_code, 200)
