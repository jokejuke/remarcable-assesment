"""Spec: demo-data (fixtures)."""

from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.accounts import DEMO_ACCOUNTS
from catalog.category_tree import get_category_tree
from catalog.models import Category, Favorite, Product, Tag


class CatalogFixtureOnlyTests(TestCase):
    fixtures = ["catalog_category", "catalog_tag", "catalog_product"]

    def test_counts(self):
        self.assertGreaterEqual(Category.objects.count(), 5)
        self.assertGreaterEqual(Tag.objects.count(), 10)
        self.assertGreaterEqual(Product.objects.count(), 20)

    def test_creates_no_users(self):
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_three_level_tree_with_products(self):
        cache.clear()
        tree = get_category_tree()
        level3 = [n.id for n in tree.nodes if tree.path(n.id).count(" > ") == 2]
        self.assertTrue(Product.objects.filter(category_id__in=level3).exists())

    def test_out_of_stock_sample_hidden_by_default(self):
        self.assertTrue(Product.objects.filter(items_available=0).exists())
        response = self.client.get(reverse("catalog:product-list"))
        self.assertLess(response.context["paginator"].count, Product.objects.count())

    def test_exact_category_paths(self):
        cache.clear()
        tree = get_category_tree()
        self.assertEqual(
            sorted(tree.path(n.id) for n in tree.nodes),
            sorted([
                "Books",
                "Electronics",
                "Electronics > Audio",
                "Electronics > Audio > Headphones",
                "Electronics > Audio > Speakers",
                "Electronics > Computers & Phones",
                "Home & Outdoors",
            ]),
        )
        self.assertEqual(Category.objects.count(), 7)

    def test_25_products_each_in_a_category_that_holds_products(self):
        self.assertEqual(Product.objects.count(), 25)
        self.assertFalse(Product.objects.filter(category__has_products=False).exists())
        self.assertEqual(Category.objects.filter(products__isnull=False).distinct().count(), 5)

    def test_every_product_has_an_http_picture_link(self):
        for p in Product.objects.all():
            with self.subTest(product=p.name):
                self.assertRegex(p.image_url, r"^https?://[^\s/]+/\S+$")

    def test_pictures_are_links_not_embedded_files(self):
        self.assertFalse(Product.objects.filter(image_url__startswith="data:").exists())

    def test_every_product_has_a_unique_slug(self):
        slugs = list(Product.objects.values_list("slug", flat=True))
        self.assertTrue(all(slugs))
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_slugs_open_the_product_pages(self):
        for product in Product.objects.all()[:5]:
            self.assertEqual(self.client.get(reverse("catalog:product-detail", args=[product.slug])).status_code, 200)

    def test_more_products_than_fit_on_one_storefront_page(self):
        response = self.client.get(reverse("catalog:product-list"), {"include_out_of_stock": "true"})
        self.assertGreater(response.context["paginator"].num_pages, 1)
        self.assertEqual(response.context["paginator"].count, 25)

    def test_cards_show_pictures_and_the_placeholder(self):
        html = self.client.get(reverse("catalog:product-list"), {"include_out_of_stock": "true", "page": 3}).content.decode()
        html += self.client.get(reverse("catalog:product-list"), {"include_out_of_stock": "true", "page": 1}).content.decode()
        self.assertIn('<img src="https://upload.wikimedia.org/', html)

    def test_products_have_several_tags_and_a_price_range(self):
        self.assertTrue(all(len(p.tags.all()) >= 2 for p in Product.objects.prefetch_related("tags")))
        prices = Product.objects.values_list("price_cents", flat=True)
        self.assertGreater(max(prices), 100 * min(prices))


class FixtureValidationTests(TestCase):
    fixtures = ["catalog_category", "catalog_tag", "catalog_product", "demo_users"]

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
        self.assertTrue(self.client.login(username="admin@example.com", password="Demo-admin-123!"))
        for url in ("admin:index", "admin:catalog_category_changelist", "admin:catalog_tag_changelist",
                    "admin:catalog_product_changelist", "admin:catalog_product_add"):
            self.assertEqual(self.client.get(reverse(url)).status_code, 200, url)

    def test_all_demo_accounts_use_their_email_as_username(self):
        users = {u.username: u for u in get_user_model().objects.all()}
        self.assertEqual(set(users), {"admin@example.com", "shopper@example.com", "shopper2@example.com"})
        for username, user in users.items():
            self.assertEqual(user.email, username)

    def test_both_shoppers_have_no_admin_access(self):
        for username, password in (("shopper@example.com", "Demo-shopper-123!"), ("shopper2@example.com", "Demo-shopper2-123!")):
            with self.subTest(username=username):
                self.assertTrue(self.client.login(username=username, password=password))
                response = self.client.get(reverse("admin:index"))
                self.assertRedirects(response, f"{reverse('admin:login')}?next={reverse('admin:index')}")
                self.client.logout()

    def test_the_old_usernames_are_gone(self):
        self.assertFalse(self.client.login(username="admin", password="Demo-admin-123!"))
        self.assertFalse(self.client.login(username="shopper", password="Demo-shopper-123!"))

    def test_email_logins_work_in_any_letter_case_through_the_login_form(self):
        response = self.client.post(reverse("login"), {"username": "Shopper2@Example.com", "password": "Demo-shopper2-123!"})
        self.assertEqual(response.status_code, 302)

    def test_shopper_has_favourites(self):
        self.assertTrue(self.client.login(username="shopper@example.com", password="Demo-shopper-123!"))
        response = self.client.get(reverse("catalog:my-favorites"))
        self.assertGreaterEqual(len(response.context["products"]), 2)

    def test_second_shopper_starts_with_no_favourites(self):
        self.assertTrue(self.client.login(username="shopper2@example.com", password="Demo-shopper2-123!"))
        response = self.client.get(reverse("catalog:my-favorites"))
        self.assertEqual(len(response.context["products"]), 0)
        self.assertFalse(Favorite.objects.filter(user__username="shopper2@example.com").exists())

    def test_demo_passwords_pass_the_signup_rules(self):
        for email, password in DEMO_ACCOUNTS:
            with self.subTest(email=email):
                validate_password(password)
                self.assertTrue(self.client.login(username=email, password=password))
                self.client.logout()

    @override_settings(DEBUG=True)
    def test_login_page_lists_demo_accounts_in_debug(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Demo accounts")
        for email, password in DEMO_ACCOUNTS:
            self.assertContains(response, email)
            self.assertContains(response, password)

    @override_settings(DEBUG=False)
    def test_login_page_hides_demo_accounts_without_debug(self):
        response = self.client.get(reverse("login"))
        self.assertNotContains(response, "Demo accounts")
        for email, password in DEMO_ACCOUNTS:
            self.assertNotContains(response, email)
            self.assertNotContains(response, password)

    def test_readme_lists_the_same_demo_accounts(self):
        readme = (Path(__file__).resolve().parents[2] / "README.md").read_text()
        for email, password in DEMO_ACCOUNTS:
            self.assertIn(f"| `{email}` | `{password}` |", readme)
