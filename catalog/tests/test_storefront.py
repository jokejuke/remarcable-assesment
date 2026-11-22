"""Spec: storefront (listing page, sidebar form, cards, login)."""

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .factories import build_tree, product, tags, user

HOME = reverse("catalog:product-list")


def urlencode_for_test(value):
    from urllib.parse import quote

    return quote(value, safe="/")


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
    def test_anonymous_sees_in_stock_products_with_details_and_buy(self):
        response = self.client.get(HOME)
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context["products"]]
        self.assertEqual(names, ["A Novel", "Budget Earbuds", "Party Speaker", "Studio Headphones"])
        self.assertNotContains(response, "Sold Out Buds")
        self.assertNotContains(response, "to buy or save favourites")
        self.assertContains(response, ">Details<", count=4)
        self.assertContains(response, 'class="button buy"', count=4)
        self.assertContains(response, reverse("catalog:product-detail", args=["budget-earbuds"]))
        self.assertNotContains(response, "Favourite")
        self.assertNotContains(response, "<form method=\"post\" action=\"/products/")

    def test_card_shows_path_tags_price_stock(self):
        response = self.client.get(HOME)
        self.assertContains(response, "Electronics &gt; Audio &gt; Headphones")
        self.assertContains(response, "$99.00")
        self.assertContains(response, "5 in stock")
        self.assertContains(response, "<span>budget</span>", html=False)

    def test_out_of_stock_card_has_details_but_no_buy(self):
        self.client.force_login(user())
        response = self.client.get(HOME, {"include_out_of_stock": "true", "q": "Sold"})
        self.assertContains(response, "Out of stock")
        self.assertContains(response, ">Details<")
        self.assertNotContains(response, 'class="buy"')

    def test_out_of_stock_card_has_no_buy_for_anonymous(self):
        response = self.client.get(HOME, {"include_out_of_stock": "true", "q": "Sold"})
        self.assertContains(response, ">Details<")
        self.assertNotContains(response, "buy")

    def test_anonymous_buy_returns_to_same_filtered_page_without_order(self):
        from catalog.models import Order

        user(username="shopper", password="pass-for-tests-123")
        page = f"{HOME}?q=wireless&category={self.t['audio'].pk}"
        response = self.client.get(page)
        login_url = f'{reverse("login")}?next={urlencode_for_test(page)}'
        self.assertContains(response, f'href="{login_url}"', html=False)
        # Follow it: the login page carries `next`, and logging in lands on the same filtered URL.
        login_page = self.client.get(login_url)
        self.assertContains(login_page, f'name="next" value="{page.replace("&", "&amp;")}"', html=False)
        response = self.client.post(reverse("login"), {"username": "shopper", "password": "pass-for-tests-123", "next": page})
        self.assertRedirects(response, page)
        self.assertFalse(Order.objects.exists())
        self.buds.refresh_from_db()
        self.assertEqual(self.buds.items_available, 5)

    def test_cards_show_placeholder_without_picture_and_image_with_one(self):
        from catalog.models import Product

        Product.objects.filter(pk=self.buds.pk).update(image_url="https://example.com/buds.jpg")
        html = self.client.get(HOME, {"q": "Earbuds"}).content.decode()
        self.assertIn('<img src="https://example.com/buds.jpg" alt="Budget Earbuds"', html)
        self.assertIn('loading="lazy"', html)
        self.assertIn('referrerpolicy="no-referrer"', html)
        self.assertIn("onerror=", html)
        html = self.client.get(HOME, {"q": "Studio"}).content.decode()
        self.assertNotIn("<img", html)
        self.assertIn('class="img-placeholder" role="img"', html)

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

    def test_reset_disabled_when_no_filters(self):
        response = self.client.get(HOME)
        self.assertFalse(response.context["filters_active"])
        self.assertContains(response, '<a class="button secondary" aria-disabled="true" role="link">Reset</a>', html=False)
        self.assertNotContains(response, f'href="{HOME}">Reset')

    def test_reset_enabled_with_a_category(self):
        response = self.client.get(HOME, {"category": self.t["audio"].pk})
        self.assertTrue(response.context["filters_active"])
        self.assertContains(response, f'<a class="button secondary" href="{HOME}">Reset</a>', html=False)

    def test_reset_disabled_for_full_price_range_only(self):
        low, high = 500, 30000  # the slider bounds of this data set
        response = self.client.get(HOME, {"price_min": low, "price_max": high})
        self.assertEqual((response.context["price_low"], response.context["price_high"]), (low, high))
        self.assertFalse(response.context["filters_active"])
        self.assertContains(response, 'aria-disabled="true"')

    def test_reset_enabled_for_each_kind_of_filter(self):
        cases = [
            {"q": "x"}, {"tags": [self.wireless.pk]}, {"tags": [self.wireless.pk], "match": "any"},
            {"include_out_of_stock": "true"}, {"price_min": 600}, {"price_max": 29900},
            {"category": 999999},  # an invalid filter is still something to reset
        ]
        for params in cases:
            with self.subTest(params=params):
                self.assertTrue(self.client.get(HOME, params).context["filters_active"])

    def test_reset_default_cases_stay_disabled(self):
        for params in ({"match": "all"}, {"match": "any"}, {"page": 1}, {"q": ""}, {"favorites": "true"}):
            with self.subTest(params=params):
                self.assertFalse(self.client.get(HOME, params).context["filters_active"])

    def test_reset_enabled_for_logged_in_favourites_filter(self):
        self.client.force_login(user())
        self.assertTrue(self.client.get(HOME, {"favorites": "true"}).context["filters_active"])

    def test_apply_is_rendered_enabled_and_actions_are_outside_the_scrolling_body(self):
        html = self.client.get(HOME).content.decode()
        self.assertRegex(html, r'<button type="submit" id="apply-filters">Apply</button>')
        self.assertLess(html.index('class="filters-body"'), html.index('class="filter-actions"'))
        body = html[html.index('class="filters-body"'):html.index('class="filter-actions"')]
        self.assertNotIn("Apply", body)

    def test_price_filter_has_two_native_sliders_for_the_no_js_fallback(self):
        html = self.client.get(HOME).content.decode()
        self.assertEqual(html.count('type="range"'), 2)
        self.assertNotIn('class="price-filter dual"', html)  # `dual` is only added by the script

    def test_category_tree_indented_by_depth(self):
        response = self.client.get(HOME)
        html = response.content.decode()
        self.assertRegex(html, r'class="tree-option depth-1"[^>]*>.*?Electronics')
        self.assertRegex(html, r'class="tree-option depth-3"[^>]*>.*?Headphones')
        self.assertLess(html.index("> All"), html.index("Electronics</label>"))

    def test_tree_options_carry_parent_and_children_data(self):
        import re

        html = self.client.get(HOME).content.decode()

        def label(name):
            return re.search(rf'<label class="tree-option[^>]*>(?:(?!</label>).)*?> {name}</label>', html, re.S).group(0)

        headphones, audio, electronics = label("Headphones"), label("Audio"), label("Electronics")
        self.assertIn(f'data-id="{self.t["headphones"].pk}"', headphones)
        self.assertIn(f'data-parent="{self.t["audio"].pk}"', headphones)
        self.assertNotIn("data-has-children", headphones)
        self.assertIn(f'data-parent="{self.t["electronics"].pk}"', audio)
        self.assertIn('data-has-children="true"', audio)
        self.assertIn('data-parent=""', electronics)
        self.assertIn('data-has-children="true"', electronics)
        all_option = re.search(r'<label class="tree-option depth-0[^>]*>', html).group(0)
        self.assertNotIn("data-id", all_option)

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


class PageSizeTests(TestCase):
    def test_25_matching_products_make_pages_of_10_10_and_5(self):
        leaf_category = build_tree()["fiction"]
        for i in range(25):
            product(f"Book {i:02d}", leaf_category)
        sizes = []
        for page in (1, 2, 3):
            response = self.client.get(HOME, {"page": page})
            sizes.append(len(response.context["products"]))
        self.assertEqual(sizes, [10, 10, 5])
        self.assertEqual(response.context["paginator"].num_pages, 3)
        self.assertEqual(self.client.get(HOME, {"page": 4}).status_code, 404)

    def test_api_page_size_is_unchanged(self):
        from django.conf import settings

        self.assertEqual(settings.REST_FRAMEWORK["PAGE_SIZE"], 20)


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


class ProductPageTests(StorefrontDataMixin, TestCase):
    def url(self, p):
        return reverse("catalog:product-detail", args=[p.slug])

    def test_page_renders_by_slug_for_anonymous(self):
        self.assertEqual(self.url(self.studio), "/products/studio-headphones/")
        response = self.client.get(self.url(self.studio))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Studio Headphones")
        self.assertContains(response, "Wireless noise-cancelling")
        self.assertContains(response, "Electronics &gt; Audio &gt; Headphones")
        self.assertContains(response, "$99.00")
        self.assertContains(response, "5 in stock")
        self.assertContains(response, "<span>wireless</span>", html=False)
        self.assertContains(response, 'class="button buy"')
        self.assertNotContains(response, "Favourite")

    def test_full_description_not_truncated(self):
        long = " ".join(f"word{i}" for i in range(60))
        from catalog.models import Product

        Product.objects.filter(pk=self.novel.pk).update(description=long)
        self.assertContains(self.client.get(self.url(self.novel)), "word59")
        self.assertNotContains(self.client.get(HOME, {"q": "word1"}), "word59")

    def test_unknown_slug_is_404(self):
        self.assertEqual(self.client.get("/products/no-such-product/").status_code, 404)

    def test_out_of_stock_product_page_has_no_buy(self):
        for visitor in (None, user()):
            if visitor:
                self.client.force_login(visitor)
            response = self.client.get(self.url(self.sold))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Out of stock")
            self.assertNotContains(response, "buy")

    def test_logged_in_page_has_favourite_and_buy(self):
        self.client.force_login(user())
        response = self.client.get(self.url(self.studio))
        self.assertContains(response, "♡ Favourite")
        self.assertContains(response, 'class="buy"')

    def test_buy_and_favourite_return_to_the_page(self):
        from catalog.models import Favorite, Order

        self.client.force_login(user())
        page = self.url(self.studio)
        response = self.client.post(reverse("catalog:buy", args=[self.studio.pk]), {"next": page}, follow=True)
        self.assertRedirects(response, page)
        self.assertContains(response, "Order #")
        self.assertEqual(Order.objects.count(), 1)
        response = self.client.post(reverse("catalog:favorite-add", args=[self.studio.pk]), {"next": page}, follow=True)
        self.assertRedirects(response, page)
        self.assertContains(response, "♥ Favourite")
        self.assertTrue(Favorite.objects.exists())

    def test_page_shows_picture_or_placeholder(self):
        from catalog.models import Product

        Product.objects.filter(pk=self.studio.pk).update(image_url="https://example.com/s.jpg")
        self.assertContains(self.client.get(self.url(self.studio)), '<img src="https://example.com/s.jpg" alt="Studio Headphones"')
        self.assertContains(self.client.get(self.url(self.novel)), 'class="img-placeholder" role="img"')

    def test_anonymous_buy_link_returns_to_the_page(self):
        response = self.client.get(self.url(self.studio))
        self.assertContains(response, f'href="{reverse("login")}?next=/products/studio-headphones/"', html=False)
