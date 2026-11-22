"""Spec: storefront (listing page, sidebar form, cards, login)."""

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .factories import build_tree, product, tags, user

HOME = reverse("catalog:product-list")


class StorefrontDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.t = t = build_tree()
        cls.wireless, cls.budget = tags("wireless", "budget")
        cls.buds = product("Budget Earbuds", t["headphones"], 500, description="Wireless in-ear",
                           tags=[cls.wireless, cls.budget])
        cls.studio = product("Studio Headphones", t["headphones"], 9900, description="Wireless noise-cancelling",
                             tags=[cls.wireless])
        cls.speaker = product("Party Speaker", t["speakers"], 30000, description="Loud wireless speaker",
                              tags=[cls.wireless])
        cls.novel = product("A Novel", t["fiction"], 1999, description="Paperback")
        cls.sold = product("Sold Out Buds", t["headphones"], 3000, items_available=0, tags=[cls.budget])

    def setUp(self):
        cache.clear()


class ProductListTests(StorefrontDataMixin, TestCase):
    def test_anonymous_sees_in_stock_products_and_login_link(self):
        response = self.client.get(HOME)
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context["products"]]
        self.assertEqual(names, ["A Novel", "Budget Earbuds", "Party Speaker", "Studio Headphones"])
        self.assertNotContains(response, "Sold Out Buds")
        self.assertContains(response, "Log in")
        self.assertNotContains(response, 'class="buy"')
        self.assertNotContains(response, "♡ Favourite")

    def test_card_shows_path_tags_price_stock(self):
        response = self.client.get(HOME)
        self.assertContains(response, "Electronics &gt; Audio &gt; Headphones")
        self.assertContains(response, "$99.00")
        self.assertContains(response, "5 in stock")
        self.assertContains(response, "<span>budget</span>", html=False)

    def test_out_of_stock_card_has_no_buy(self):
        self.client.force_login(user())
        response = self.client.get(HOME, {"include_out_of_stock": "true", "q": "Sold"})
        self.assertContains(response, "Out of stock")
        self.assertNotContains(response, 'class="buy"')

    def test_logged_in_cards_have_buy_and_favourite(self):
        self.client.force_login(user())
        response = self.client.get(HOME)
        self.assertContains(response, 'class="buy"')
        self.assertContains(response, "♡ Favourite")

    def test_filters_combine(self):
        response = self.client.get(HOME, {"q": "wireless", "category": self.t["audio"].pk,
                                          "tags": [self.budget.pk], "price_max": 10000})
        self.assertEqual([p.name for p in response.context["products"]], ["Budget Earbuds"])

    def test_apply_category_and_tags(self):
        response = self.client.get(HOME, {"category": self.t["headphones"].pk,
                                          "tags": [self.wireless.pk, self.budget.pk]})
        self.assertEqual([p.name for p in response.context["products"]], ["Budget Earbuds"])

    def test_invalid_filter_shows_form_error(self):
        response = self.client.get(HOME, {"category": 999999})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please fix the filter errors")
        self.assertIn("category", response.context["form"].errors)
        response = self.client.get(HOME, {"price_min": 5000, "price_max": 100})
        self.assertIn("price_max", response.context["form"].errors)

    def test_favorites_filter_ignored_for_anonymous(self):
        response = self.client.get(HOME, {"favorites": "true"})
        self.assertEqual(len(response.context["products"]), 4)
        self.assertNotContains(response, 'name="favorites"')


class SidebarFormTests(StorefrontDataMixin, TestCase):
    def test_single_get_form_with_header_search_attached(self):
        response = self.client.get(HOME)
        self.assertContains(response, '<form id="filters" method="get"', html=False)
        self.assertContains(response, 'name="q" form="filters"', html=False)
        for control in ['name="category"', 'name="tags"', 'name="match"', 'name="price_min"',
                        'name="price_max"', 'name="include_out_of_stock"', ">Apply<", ">Reset<"]:
            self.assertContains(response, control, html=False)

    def test_controls_show_selected_state(self):
        response = self.client.get(HOME, {
            "q": "wireless", "category": self.t["audio"].pk, "tags": [self.budget.pk],
            "match": "any", "include_out_of_stock": "true", "price_min": 1000, "price_max": 20000,
        })
        html = response.content.decode()
        self.assertIn('value="wireless"', html)
        self.assertRegex(html, rf'value="{self.t["audio"].pk}"[^>]*checked')
        self.assertRegex(html, rf'value="{self.budget.pk}"[^>]*checked')
        self.assertIn('value="any" checked', html)
        self.assertIn('name="include_out_of_stock" value="true" checked', html)
        self.assertRegex(html, r'id="price_min"[^>]*value="1000"')
        self.assertRegex(html, r'id="price_max"[^>]*value="20000"')

    def test_reset_is_a_plain_link_to_defaults(self):
        response = self.client.get(HOME, {"q": "x"})
        self.assertContains(response, f'<a class="button secondary" href="{HOME}">Reset</a>', html=False)
        response = self.client.get(HOME)
        self.assertEqual(len(response.context["products"]), 4)
        self.assertRegex(response.content.decode(), r'value=""[^>]*checked[^>]*> All')

    def test_category_tree_indented_by_depth(self):
        response = self.client.get(HOME)
        html = response.content.decode()
        self.assertRegex(html, r'class="tree-option depth-1"[^>]*>.*?Electronics')
        self.assertRegex(html, r'class="tree-option depth-3"[^>]*>.*?Headphones')
        self.assertLess(html.index("> All"), html.index("Electronics</label>"))

    def test_slider_bounds_match_cheapest_and_most_expensive(self):
        response = self.client.get(HOME)
        self.assertEqual((response.context["price_low"], response.context["price_high"]), (500, 30000))
        html = response.content.decode()
        self.assertRegex(html, r'id="price_min" name="price_min" min="500" max="30000" step="100"')
        self.assertContains(response, "$5.00")
        self.assertContains(response, "$300.00")

    def test_price_filter_works_without_js(self):
        response = self.client.get(HOME, {"price_min": 1000, "price_max": 10000})
        self.assertEqual([p.name for p in response.context["products"]], ["A Novel", "Studio Headphones"])


class PaginationTests(StorefrontDataMixin, TestCase):
    def test_page_two_keeps_filters(self):
        from catalog.views import ProductListView

        ProductListView.paginate_by, old = 2, ProductListView.paginate_by
        self.addCleanup(setattr, ProductListView, "paginate_by", old)
        response = self.client.get(HOME, {"q": "wireless"})
        self.assertContains(response, "?q=wireless&amp;page=2")
        response = self.client.get(HOME, {"q": "wireless", "page": 2})
        self.assertEqual([p.name for p in response.context["products"]], ["Studio Headphones"])


class LoginTests(StorefrontDataMixin, TestCase):
    def test_login_redirects_to_next_and_header_shows_username(self):
        user(username="shopper", password="pass-for-tests-123")
        next_url = f"{HOME}?q=wireless"
        response = self.client.post(reverse("login"), {"username": "shopper", "password": "pass-for-tests-123", "next": next_url})
        self.assertRedirects(response, next_url)
        response = self.client.get(next_url)
        self.assertContains(response, "Signed in as <strong>shopper</strong>", html=False)

    def test_login_page_renders(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)

    def test_logout_is_post_only(self):
        self.client.force_login(user())
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, HOME)

    def test_page_source_has_no_tokens(self):
        self.client.force_login(user())
        html = self.client.get(HOME).content.decode()
        self.assertNotIn("access", html.lower().replace("accessible", ""))
        self.assertNotIn("refresh", html.lower())
        self.assertNotIn("eyJ", html)  # JWTs start with a base64 '{"'
