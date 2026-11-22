"""Spec: catalog-api, plus the API side of favorites and checkout."""

from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from catalog.models import Favorite, Order, Product

from .factories import build_tree, product, tags, user


class ApiDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.t = t = build_tree()
        cls.wireless, cls.budget = tags("wireless", "budget")
        cls.buds = product("Budget Earbuds", t["headphones"], 2500, description="Wireless in-ear",
                           tags=[cls.wireless, cls.budget])
        cls.studio = product("Studio Headphones", t["headphones"], 9900, description="Wireless noise-cancelling",
                             tags=[cls.wireless])
        cls.speaker = product("Party Speaker", t["speakers"], 15000, description="Wireless speaker",
                              tags=[cls.wireless])
        cls.novel = product("A Novel", t["fiction"], 1999)
        cls.sold = product("Sold Out Buds", t["headphones"], 3000, items_available=0, tags=[cls.budget])
        cls.shopper = user("shopper")
        cls.other = user("other")

    def setUp(self):
        cache.clear()


class CatalogEndpointTests(ApiDataMixin, APITestCase):
    def test_list_products_anonymously(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 4)
        self.assertIn("results", response.data)

    def test_product_detail_fields_anonymous(self):
        response = self.client.get(f"/api/products/{self.buds.pk}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["price_cents"], 2500)
        self.assertEqual(data["price"], "$25.00")
        self.assertEqual(data["category"], {"id": self.t["headphones"].pk, "name": "Headphones",
                                            "path": "Electronics > Audio > Headphones"})
        self.assertEqual({t["name"] for t in data["tags"]}, {"wireless", "budget"})
        for field in ("id", "name", "description", "items_available", "created_at", "updated_at"):
            self.assertIn(field, data)
        self.assertNotIn("is_favorite", data)

    def test_authenticated_detail_has_is_favorite(self):
        Favorite.objects.create(user=self.shopper, product=self.buds)
        self.client.force_authenticate(self.shopper)
        self.assertIs(self.client.get(f"/api/products/{self.buds.pk}/").data["is_favorite"], True)
        self.assertIs(self.client.get(f"/api/products/{self.studio.pk}/").data["is_favorite"], False)

    def test_out_of_stock_detail_is_readable(self):
        self.assertEqual(self.client.get(f"/api/products/{self.sold.pk}/").status_code, 200)

    def test_write_methods_rejected(self):
        for url in ("/api/products/", "/api/categories/", "/api/tags/"):
            self.assertEqual(self.client.post(url, {}).status_code, 405, url)
        detail_urls = [f"/api/products/{self.buds.pk}/", f"/api/categories/{self.t['audio'].pk}/",
                       f"/api/tags/{self.budget.pk}/"]
        for url in detail_urls:
            for method in ("put", "patch", "delete"):
                self.assertEqual(getattr(self.client, method)(url, {}).status_code, 405, (method, url))
        self.assertEqual(Product.objects.count(), 5)

    def test_filtered_list(self):
        response = self.client.get("/api/products/", {"q": "wireless", "category": self.t["audio"].pk,
                                                      "tags": [self.wireless.pk, self.budget.pk], "match": "any"})
        self.assertEqual([p["name"] for p in response.data["results"]],
                         ["Budget Earbuds", "Party Speaker", "Studio Headphones"])

    def test_invalid_filters_return_400_with_field_errors(self):
        response = self.client.get("/api/products/", {"category": "abc"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.json())
        response = self.client.get("/api/products/", {"price_min": 500, "price_max": 100})
        self.assertEqual(response.status_code, 400)
        self.assertIn("price_max", response.json())
        self.assertNotIn("Traceback", response.content.decode())

    def test_favorites_filter_anonymous_is_401(self):
        response = self.client.get("/api/products/", {"favorites": "true"})
        self.assertEqual(response.status_code, 401)

    def test_favorites_filter_authenticated(self):
        Favorite.objects.create(user=self.shopper, product=self.novel)
        self.client.force_authenticate(self.shopper)
        response = self.client.get("/api/products/", {"favorites": "true"})
        self.assertEqual([p["id"] for p in response.data["results"]], [self.novel.pk])

    def test_categories_show_tree(self):
        response = self.client.get("/api/categories/")
        self.assertEqual(response.status_code, 200)
        rows = {row["name"]: row for row in response.data["results"]}
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows["Headphones"]["parent"], self.t["audio"].pk)
        self.assertEqual(rows["Headphones"]["path"], "Electronics > Audio > Headphones")
        self.assertTrue(rows["Headphones"]["has_products"])
        self.assertTrue(rows["Audio"]["has_subcategories"])

    def test_tags_list(self):
        self.assertEqual([t["name"] for t in self.client.get("/api/tags/").data["results"]], ["budget", "wireless"])


class ParityTests(ApiDataMixin, APITestCase):
    def collect_storefront(self, query):
        ids, page = [], 1
        while True:
            response = self.client.get(reverse("catalog:product-list"), {**query, "page": page})
            ids += [p.pk for p in response.context["products"]]
            if not response.context["page_obj"].has_next():
                return ids
            page += 1

    def collect_api(self, query):
        ids, url, params = [], "/api/products/", query
        while url:
            data = self.client.get(url, params).json()
            ids += [p["id"] for p in data["results"]]
            url, params = data["next"], None
        return ids

    def test_same_ids_same_order(self):
        for i in range(30):  # more than one page in both (12 and 20 per page)
            product(f"Extra {i:02d} wireless", self.t["speakers"], 1000 + i, tags=[self.wireless])
        queries = [
            {},
            {"q": "wireless"},
            {"category": self.t["electronics"].pk, "tags": [self.wireless.pk, self.budget.pk], "match": "any"},
            {"include_out_of_stock": "true", "price_min": 1000, "price_max": 5000},
        ]
        for query in queries:
            with self.subTest(query=query):
                storefront, api = self.collect_storefront(query), self.collect_api(query)
                self.assertTrue(storefront)
                self.assertEqual(storefront, api)


class SchemaTests(APITestCase):
    def test_schema_lists_filters_and_409(self):
        response = self.client.get("/api/schema/", HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertTrue(schema["openapi"].startswith("3."))
        params = {p["name"] for p in schema["paths"]["/api/products/"]["get"]["parameters"]}
        self.assertTrue({"q", "category", "tags", "match", "price_min", "price_max",
                         "include_out_of_stock", "favorites", "page"} <= params)
        self.assertIn("409", schema["paths"]["/api/orders/"]["post"]["responses"])
        self.assertIn("jwtAuth", schema["components"]["securitySchemes"])
        self.assertIn("/api/favorites/{product_id}/", schema["paths"])

    def test_swagger_ui(self):
        response = self.client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "swagger")


class FavoritesApiTests(ApiDataMixin, APITestCase):
    def test_anonymous_401(self):
        self.assertEqual(self.client.get("/api/favorites/").status_code, 401)
        self.assertEqual(self.client.post("/api/favorites/", {"product": self.buds.pk}).status_code, 401)
        self.assertEqual(self.client.delete(f"/api/favorites/{self.buds.pk}/").status_code, 401)

    def test_add_201_then_200(self):
        self.client.force_authenticate(self.shopper)
        first = self.client.post("/api/favorites/", {"product": self.buds.pk}, format="json")
        self.assertEqual(first.status_code, 201)
        second = self.client.post("/api/favorites/", {"product": self.buds.pk}, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Favorite.objects.filter(user=self.shopper, product=self.buds).count(), 1)

    def test_remove_204_either_way(self):
        Favorite.objects.create(user=self.shopper, product=self.buds)
        self.client.force_authenticate(self.shopper)
        self.assertEqual(self.client.delete(f"/api/favorites/{self.buds.pk}/").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/favorites/{self.buds.pk}/").status_code, 204)
        self.assertFalse(Favorite.objects.exists())

    def test_unknown_product_400(self):
        self.client.force_authenticate(self.shopper)
        response = self.client.post("/api/favorites/", {"product": 999999}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("product", response.json())

    def test_lists_are_private(self):
        Favorite.objects.create(user=self.shopper, product=self.buds)
        Favorite.objects.create(user=self.other, product=self.novel)
        self.client.force_authenticate(self.other)
        rows = self.client.get("/api/favorites/").data["results"]
        self.assertEqual([r["product"]["id"] for r in rows], [self.novel.pk])
        self.assertTrue(rows[0]["product"]["is_favorite"])

    def test_cannot_remove_someone_elses(self):
        Favorite.objects.create(user=self.shopper, product=self.buds)
        self.client.force_authenticate(self.other)
        self.client.delete(f"/api/favorites/{self.buds.pk}/")
        self.assertTrue(Favorite.objects.filter(user=self.shopper).exists())


class OrdersApiTests(ApiDataMixin, APITestCase):
    def place(self, items):
        return self.client.post("/api/orders/", {"items": items}, format="json")

    def test_place_order_201_with_total(self):
        self.client.force_authenticate(self.shopper)
        response = self.place([{"product": self.buds.pk, "quantity": 2}, {"product": self.novel.pk, "quantity": 1}])
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data["total_cents"], 2 * 2500 + 1999)
        self.assertEqual(response.data["total"], "$69.99")
        self.assertEqual(len(response.data["items"]), 2)
        self.buds.refresh_from_db()
        self.assertEqual(self.buds.items_available, 3)

    def test_validation_errors_400(self):
        self.client.force_authenticate(self.shopper)
        cases = {
            "empty": [],
            "zero quantity": [{"product": self.buds.pk, "quantity": 0}],
            "unknown product": [{"product": 999999, "quantity": 1}],
            "duplicate": [{"product": self.buds.pk, "quantity": 1}, {"product": self.buds.pk, "quantity": 1}],
        }
        for label, items in cases.items():
            with self.subTest(label):
                self.assertEqual(self.place(items).status_code, 400)
        self.assertFalse(Order.objects.exists())
        self.buds.refresh_from_db()
        self.assertEqual(self.buds.items_available, 5)

    def test_409_lists_every_short_product(self):
        self.client.force_authenticate(self.shopper)
        response = self.place([{"product": self.buds.pk, "quantity": 1},
                               {"product": self.sold.pk, "quantity": 1},
                               {"product": self.novel.pk, "quantity": 99}])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"out_of_stock": sorted([self.sold.pk, self.novel.pk])})
        self.assertFalse(Order.objects.exists())
        self.buds.refresh_from_db()
        self.assertEqual(self.buds.items_available, 5)

    def test_other_users_orders_404(self):
        self.client.force_authenticate(self.shopper)
        mine = self.place([{"product": self.buds.pk, "quantity": 1}]).data["id"]
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/orders/{mine}/").status_code, 404)
        self.assertEqual(self.client.get("/api/orders/").data["count"], 0)
        self.client.force_authenticate(self.shopper)
        self.assertEqual(self.client.get(f"/api/orders/{mine}/").status_code, 200)

    def test_anonymous_401(self):
        response = self.place([{"product": self.buds.pk, "quantity": 1}])
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Order.objects.exists())
