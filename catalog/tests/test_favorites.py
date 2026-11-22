"""Spec: favorites (model, queryset, storefront views)."""

from django.core.cache import cache
from django.db import IntegrityError, connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from catalog.filters import ProductFilterSet
from catalog.models import Favorite, Product

from .factories import build_tree, product, tags, user

HOME = reverse("catalog:product-list")


class FavoriteModelTests(TestCase):
    def setUp(self):
        self.t = build_tree()
        self.p = product("Buds", self.t["headphones"])
        self.u = user()

    def test_duplicate_pair_rejected(self):
        Favorite.objects.create(user=self.u, product=self.p)
        with self.assertRaises(IntegrityError):
            Favorite.objects.create(user=self.u, product=self.p)

    def test_new_row_has_both_timestamps(self):
        f = Favorite.objects.create(user=self.u, product=self.p)
        self.assertEqual(f.created_at, f.updated_at)
        self.assertGreater(f.created_at, 1_700_000_000)

    def test_deleting_user_removes_favourites(self):
        Favorite.objects.create(user=self.u, product=self.p)
        self.u.delete()
        self.assertFalse(Favorite.objects.exists())

    def test_deleting_product_removes_favourites(self):
        Favorite.objects.create(user=self.u, product=self.p)
        self.p.delete()
        self.assertFalse(Favorite.objects.exists())


class FavoriteQueryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.t = build_tree()
        self.a, self.b = user("alice"), user("bob")
        self.p7 = product("Seven", self.t["headphones"])
        self.p8 = product("Eight", self.t["headphones"])
        self.p9 = product("Nine", self.t["headphones"])
        Favorite.objects.create(user=self.a, product=self.p7)
        Favorite.objects.create(user=self.b, product=self.p8)

    def test_favorites_of_is_private(self):
        self.assertEqual(list(Product.objects.favorites_of(self.a)), [self.p7])

    def test_is_favorite_flag(self):
        flags = dict(Product.objects.with_is_favorite(self.a).values_list("name", "is_favorite"))
        self.assertEqual(flags, {"Seven": True, "Eight": False, "Nine": False})

    def test_only_favourites_filter_for_logged_in_user(self):
        request = RequestFactory().get("/", {"favorites": "true"})
        request.user = self.a
        fs = ProductFilterSet(request.GET, queryset=Product.objects.for_listing(self.a), request=request)
        self.assertEqual([p.name for p in fs.qs], ["Seven"])

    def test_query_count_fixed_with_is_favorite(self):
        def count(n):
            Product.objects.exclude(pk__in=[self.p7.pk]).delete()
            for i in range(n - 1):
                product(f"Item {i:02d}", self.t["headphones"], tags=tags(f"t{n}-{i}"))
            with CaptureQueriesContext(connection) as ctx:
                rows = [(p.is_favorite, list(p.tags.all())) for p in Product.objects.for_listing(self.a)]
            self.assertEqual(len(rows), n)
            return len(ctx.captured_queries)

        self.assertEqual(count(5), count(20))


class FavoriteViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.t = build_tree()
        self.p = product("Buds", self.t["headphones"])
        self.sold = product("Gone", self.t["headphones"], items_available=0)
        self.u = user()
        self.client.force_login(self.u)
        self.add = reverse("catalog:favorite-add", args=[self.p.pk])
        self.remove = reverse("catalog:favorite-remove", args=[self.p.pk])

    def test_add_twice_keeps_one(self):
        next_url = f"{HOME}?q=Buds"
        response = self.client.post(self.add, {"next": next_url})
        self.assertRedirects(response, next_url)
        self.client.post(self.add, {"next": next_url})
        self.assertEqual(Favorite.objects.filter(user=self.u, product=self.p).count(), 1)
        page = self.client.get(next_url)
        self.assertContains(page, "♥ Favourite")

    def test_remove_twice_is_safe(self):
        Favorite.objects.create(user=self.u, product=self.p)
        self.assertEqual(self.client.post(self.remove).status_code, 302)
        self.assertEqual(self.client.post(self.remove).status_code, 302)
        self.assertFalse(Favorite.objects.exists())

    def test_anonymous_redirected_to_login_and_back(self):
        self.client.logout()
        next_url = f"{HOME}?q=Buds"
        response = self.client.post(self.add, {"next": next_url})
        self.assertRedirects(response, f"{reverse('login')}?next=/%3Fq%3DBuds", fetch_redirect_response=False)
        self.assertFalse(Favorite.objects.exists())

    def test_external_next_falls_back_to_home(self):
        response = self.client.post(self.add, {"next": "https://evil.example/"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.add).status_code, 405)
        self.assertEqual(self.client.get(self.remove).status_code, 405)
        self.assertFalse(Favorite.objects.exists())

    def test_unknown_product_404(self):
        self.assertEqual(self.client.post(reverse("catalog:favorite-add", args=[999999])).status_code, 404)

    def test_only_favourites_checkbox_for_logged_in(self):
        self.assertContains(self.client.get(HOME), 'name="favorites"')

    def test_my_favorites_includes_out_of_stock(self):
        Favorite.objects.create(user=self.u, product=self.p)
        Favorite.objects.create(user=self.u, product=self.sold)
        other = user("other")
        Favorite.objects.create(user=other, product=product("Theirs", self.t["speakers"]))
        response = self.client.get(reverse("catalog:my-favorites"))
        self.assertEqual({p.name for p in response.context["products"]}, {"Buds", "Gone"})
        self.assertContains(response, "Out of stock")

    def test_my_favorites_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("catalog:my-favorites"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
