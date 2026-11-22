"""Spec: product-search (queryset methods and the shared FilterSet)."""

from django.core.cache import cache
from django.db import connection
from django.http import QueryDict
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from catalog.filters import ProductFilterSet
from catalog.models import Product

from .factories import build_tree, product, tags


class SearchDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.t = t = build_tree()
        cls.wireless, cls.budget, cls.premium = tags("wireless", "budget", "premium")
        cls.p = {
            "nc": product("Studio Headphones", t["headphones"], 9900,
                          description="Noise-cancelling wireless headphones", tags=[cls.wireless, cls.premium]),
            "buds": product("Budget Earbuds", t["headphones"], 2500,
                            description="Wireless in-ear", tags=[cls.wireless, cls.budget]),
            "wired": product("Wired Headset", t["headphones"], 1500,
                             description="Cable, bluetooth free", tags=[cls.budget]),
            "speaker": product("Party Speaker", t["speakers"], 15000,
                               description="Loud wireless bluetooth speaker", tags=[cls.wireless]),
            "laptop": product("Laptop Pro", t["computers"], 150000, description="Fast laptop", tags=[cls.premium]),
            "novel": product("A Novel", t["fiction"], 1999, description="A wireless-free story"),
            "sold": product("Sold Out Buds", t["headphones"], 3000, items_available=0,
                            description="Wireless", tags=[cls.wireless, cls.budget]),
        }

    def setUp(self):
        cache.clear()

    def names(self, qs):
        return set(qs.values_list("name", flat=True))


class ProductQuerySetTests(SearchDataMixin, TestCase):
    def test_all_words_present(self):
        self.assertIn("Studio Headphones", self.names(Product.objects.search("wireless noise")))

    def test_one_word_missing(self):
        result = self.names(Product.objects.search("wireless bluetooth"))
        self.assertEqual(result, {"Party Speaker"})

    def test_word_in_name_only(self):
        self.assertEqual(self.names(Product.objects.search("earbuds")), {"Budget Earbuds"})

    def test_case_insensitive(self):
        self.assertEqual(self.names(Product.objects.search("LAPTOP")), {"Laptop Pro"})

    def test_empty_search_is_no_filter(self):
        self.assertEqual(Product.objects.search("  ").count(), Product.objects.count())

    def test_top_level_category_includes_descendants(self):
        result = self.names(Product.objects.in_category(self.t["electronics"].pk))
        self.assertEqual(result, {"Studio Headphones", "Budget Earbuds", "Wired Headset", "Party Speaker", "Laptop Pro", "Sold Out Buds"})

    def test_leaf_category(self):
        result = self.names(Product.objects.in_category(self.t["speakers"].pk))
        self.assertEqual(result, {"Party Speaker"})

    def test_tags_all(self):
        result = self.names(Product.objects.with_tags([self.wireless.pk, self.budget.pk], "all"))
        self.assertEqual(result, {"Budget Earbuds", "Sold Out Buds"})

    def test_tags_any_no_duplicates(self):
        qs = Product.objects.with_tags([self.wireless.pk, self.budget.pk], "any")
        names = list(qs.values_list("name", flat=True))
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), {"Studio Headphones", "Budget Earbuds", "Wired Headset", "Party Speaker", "Sold Out Buds"})

    def test_price_between_inclusive(self):
        result = self.names(Product.objects.price_between(2500, 9900))
        self.assertEqual(result, {"Studio Headphones", "Budget Earbuds", "Sold Out Buds"})

    def test_in_stock(self):
        self.assertNotIn("Sold Out Buds", self.names(Product.objects.in_stock()))

    def test_for_listing_ordered_by_name(self):
        names = list(Product.objects.for_listing().values_list("name", flat=True))
        self.assertEqual(names, sorted(names))


class ProductFilterSetTests(SearchDataMixin, TestCase):
    def run_filter(self, query, user=None):
        request = RequestFactory().get("/", QueryDict(query, mutable=False))
        if user is not None:
            request.user = user
        else:
            from django.contrib.auth.models import AnonymousUser

            request.user = AnonymousUser()
        fs = ProductFilterSet(request.GET, queryset=Product.objects.for_listing(request.user), request=request)
        return fs

    def test_no_filters_returns_all_in_stock(self):
        fs = self.run_filter("")
        self.assertTrue(fs.is_valid())
        self.assertEqual(self.names(fs.qs), self.names(Product.objects.in_stock()))

    def test_include_out_of_stock(self):
        self.assertIn("Sold Out Buds", self.names(self.run_filter("include_out_of_stock=true").qs))
        self.assertIn("Sold Out Buds", self.names(self.run_filter("include_out_of_stock=1").qs))

    def test_default_match_is_all(self):
        fs = self.run_filter(f"tags={self.wireless.pk}&tags={self.budget.pk}")
        self.assertEqual(self.names(fs.qs), {"Budget Earbuds"})

    def test_match_any(self):
        fs = self.run_filter(f"tags={self.wireless.pk}&tags={self.budget.pk}&match=any")
        self.assertEqual(self.names(fs.qs), {"Studio Headphones", "Budget Earbuds", "Wired Headset", "Party Speaker"})

    def test_price_range_in_cents(self):
        fs = self.run_filter("price_min=2000&price_max=15000")
        self.assertEqual(self.names(fs.qs), {"Studio Headphones", "Budget Earbuds", "Party Speaker"})

    def test_combined_filters(self):
        fs = self.run_filter(f"q=wireless&category={self.t['audio'].pk}&tags={self.budget.pk}&price_max=10000")
        self.assertTrue(fs.is_valid(), fs.errors)
        self.assertEqual(self.names(fs.qs), {"Budget Earbuds"})

    def test_unknown_category_is_invalid(self):
        fs = self.run_filter("category=999999")
        self.assertFalse(fs.is_valid())
        self.assertIn("category", fs.errors)

    def test_non_numeric_category_is_invalid(self):
        fs = self.run_filter("category=abc")
        self.assertFalse(fs.is_valid())
        self.assertIn("category", fs.errors)

    def test_inverted_price_range_is_invalid(self):
        fs = self.run_filter("price_min=5000&price_max=1000")
        self.assertFalse(fs.is_valid())
        self.assertIn("price_max", fs.errors)

    def test_unknown_tag_is_invalid(self):
        fs = self.run_filter("tags=999999")
        self.assertFalse(fs.is_valid())
        self.assertIn("tags", fs.errors)

    def test_favorites_ignored_for_anonymous(self):
        fs = self.run_filter("favorites=true")
        self.assertEqual(self.names(fs.qs), self.names(Product.objects.in_stock()))


class ListingQueryCountTests(TestCase):
    def setUp(self):
        cache.clear()
        self.t = build_tree()
        self.tags = tags("a", "b", "c")

    def count_queries(self, n):
        Product.objects.all().delete()
        for i in range(n):
            product(f"Item {i:02d}", self.t["headphones"], tags=self.tags, description="match me")
        request = RequestFactory().get("/", {"q": "match", "category": self.t["audio"].pk, "tags": [self.tags[0].pk]})
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()
        fs = ProductFilterSet(request.GET, queryset=Product.objects.for_listing(request.user), request=request)
        fs.is_valid()  # validation queries (tags lookup) happen before counting
        from catalog.category_tree import get_category_tree

        get_category_tree()
        with CaptureQueriesContext(connection) as ctx:
            rows = [(p.name, p.category.name, [t.name for t in p.tags.all()], get_category_tree().path(p.category_id))
                    for p in fs.qs]
        self.assertEqual(len(rows), n)
        return len(ctx.captured_queries)

    def test_same_query_count_for_5_and_20(self):
        self.assertEqual(self.count_queries(5), self.count_queries(20))
        self.assertEqual(self.count_queries(5), 2)  # products (+category join) and tags
