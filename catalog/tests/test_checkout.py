"""Spec: checkout (models, place_order, concurrency, storefront Buy, My orders, admin)."""

import threading
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.models import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from catalog.models import Order, OrderItem, Product
from catalog.services import OutOfStock, place_order
from catalog.tests.factories import build_tree, product, user


class OrderModelTests(TestCase):
    def setUp(self):
        self.t = build_tree()
        self.u = user()
        self.p = product("Buds", self.t["headphones"])
        self.order = Order.objects.create(user=self.u, total_cents=0)

    def test_quantity_zero_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderItem.objects.create(order=self.order, product=self.p, quantity=0, unit_price_cents=1)

    def test_duplicate_product_rejected(self):
        OrderItem.objects.create(order=self.order, product=self.p, quantity=1, unit_price_cents=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderItem.objects.create(order=self.order, product=self.p, quantity=2, unit_price_cents=1)

    def test_ordered_product_cannot_be_deleted(self):
        OrderItem.objects.create(order=self.order, product=self.p, quantity=1, unit_price_cents=1)
        with self.assertRaises(ProtectedError):
            self.p.delete()

    def test_user_with_orders_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.u.delete()

    def test_bulk_create_sets_timestamps(self):
        (item,) = OrderItem.objects.bulk_create(
            [OrderItem(order=self.order, product=self.p, quantity=1, unit_price_cents=1)]
        )
        item = OrderItem.objects.get(pk=item.pk) if item.pk else OrderItem.objects.get()
        self.assertGreater(item.created_at, 1_700_000_000)
        self.assertEqual(item.created_at, item.updated_at)


class PlaceOrderTests(TestCase):
    def setUp(self):
        self.t = build_tree()
        self.u = user()
        self.p7 = product("Seven", self.t["headphones"], price_cents=4900, items_available=5)
        self.p3 = product("Three", self.t["headphones"], price_cents=1000, items_available=0)
        self.p9 = product("Nine", self.t["speakers"], price_cents=2500, items_available=1)

    def test_success_decrements_stock_and_copies_prices(self):
        order = place_order(self.u, [(self.p7.pk, 2), (self.p9.pk, 1)])
        self.assertEqual(order.total_cents, 2 * 4900 + 2500)
        items = {i.product_id: (i.quantity, i.unit_price_cents) for i in order.items.all()}
        self.assertEqual(items, {self.p7.pk: (2, 4900), self.p9.pk: (1, 2500)})
        self.p7.refresh_from_db()
        self.p9.refresh_from_db()
        self.assertEqual((self.p7.items_available, self.p9.items_available), (3, 0))

    def test_one_short_item_rolls_back_everything(self):
        with self.assertRaises(OutOfStock) as ctx:
            place_order(self.u, [(self.p7.pk, 1), (self.p3.pk, 1)])
        self.assertEqual(ctx.exception.product_ids, [self.p3.pk])
        self.p7.refresh_from_db()
        self.assertEqual(self.p7.items_available, 5)
        self.assertFalse(Order.objects.exists())

    def test_lists_every_short_product(self):
        with self.assertRaises(OutOfStock) as ctx:
            place_order(self.u, [(self.p3.pk, 1), (self.p9.pk, 2), (self.p7.pk, 1)])
        self.assertEqual(ctx.exception.product_ids, sorted([self.p3.pk, self.p9.pk]))

    def test_repricing_leaves_order_unchanged(self):
        order = place_order(self.u, [(self.p7.pk, 1)])
        self.p7.price_cents = 5900
        self.p7.save()
        order.refresh_from_db()
        self.assertEqual(order.total_cents, 4900)
        self.assertEqual(order.items.get().unit_price_cents, 4900)

    def test_sequential_race_for_last_unit(self):
        other = user("other")
        place_order(self.u, [(self.p9.pk, 1)])
        with self.assertRaises(OutOfStock):
            place_order(other, [(self.p9.pk, 1)])
        self.assertEqual(Order.objects.count(), 1)
        self.p9.refresh_from_db()
        self.assertEqual(self.p9.items_available, 0)

    def test_updated_at_set_on_decrement(self):
        Product.objects.filter(pk=self.p7.pk).update(updated_at=1000)
        with mock.patch("catalog.services.unix_now", return_value=5000):
            place_order(self.u, [(self.p7.pk, 1)])
        self.p7.refresh_from_db()
        self.assertEqual(self.p7.updated_at, 5000)


class ConcurrentCheckoutTests(TransactionTestCase):
    """Two threads, two database connections, one unit of stock."""

    def test_race_for_last_unit(self):
        t = build_tree()
        p = product("Last One", t["headphones"], items_available=1)
        buyers = [user("a"), user("b")]
        barrier = threading.Barrier(2)
        results = []

        def buy(u):
            try:
                barrier.wait(timeout=5)
                place_order(u, [(p.pk, 1)])
                results.append("ok")
            except OutOfStock:
                results.append("out")
            except Exception as exc:  # surfaced in the assertion message
                results.append(repr(exc))
            finally:
                close_old_connections()
                connection.close()

        threads = [threading.Thread(target=buy, args=(u,)) for u in buyers]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=30)

        self.assertEqual(sorted(results), ["ok", "out"], results)
        p.refresh_from_db()
        self.assertEqual(p.items_available, 0)
        self.assertEqual(Order.objects.count(), 1)


class StorefrontCheckoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.t = build_tree()
        self.u = user()
        self.p = product("Buds", self.t["headphones"], price_cents=4900, items_available=3)
        self.client.force_login(self.u)
        self.buy_url = reverse("catalog:buy", args=[self.p.pk])

    def test_buy_creates_order_and_decrements_stock(self):
        response = self.client.post(self.buy_url, {"next": "/?q=Buds"}, follow=True)
        self.assertRedirects(response, "/?q=Buds")
        self.assertContains(response, "placed: 1 × Buds")
        self.p.refresh_from_db()
        self.assertEqual(self.p.items_available, 2)
        order = Order.objects.get(user=self.u)
        self.assertEqual((order.total_cents, order.items.get().quantity), (4900, 1))

    def test_sold_out_buy_shows_message_and_creates_nothing(self):
        Product.objects.filter(pk=self.p.pk).update(items_available=0)
        response = self.client.post(self.buy_url, follow=True)
        self.assertContains(response, "out of stock")
        self.assertFalse(Order.objects.exists())

    def test_buy_requires_post_and_login(self):
        self.assertEqual(self.client.get(self.buy_url).status_code, 405)
        self.client.logout()
        response = self.client.post(self.buy_url)
        self.assertIn(reverse("login"), response.url)
        self.assertFalse(Order.objects.exists())

    def test_external_next_falls_back_to_home(self):
        response = self.client.post(self.buy_url, {"next": "https://evil.example"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_my_orders_newest_first_with_items_and_totals(self):
        other = product("Speaker", self.t["speakers"], price_cents=1000, items_available=5)
        with mock.patch("catalog.models.unix_now", return_value=1000):
            first = place_order(self.u, [(self.p.pk, 2)])
        with mock.patch("catalog.models.unix_now", return_value=2000):
            second = place_order(self.u, [(other.pk, 1), (self.p.pk, 1)])
        place_order(user("someone"), [(other.pk, 1)])
        response = self.client.get(reverse("catalog:my-orders"))
        self.assertEqual(list(response.context["orders"]), [second, first])
        self.assertContains(response, "$98.00")
        self.assertContains(response, "$59.00")

    def test_my_orders_time_is_a_time_element_with_utc_fallback(self):
        order = place_order(self.u, [(self.p.pk, 1)])
        Order.objects.filter(pk=order.pk).update(created_at=1700000000)
        response = self.client.get(reverse("catalog:my-orders"))
        self.assertContains(
            response, '<time class="local-time" datetime="2023-11-14T22:13:20Z">2023-11-14 22:13 UTC</time>', html=False
        )
        self.assertContains(response, "Intl.DateTimeFormat")

    def test_my_orders_query_count_fixed(self):
        def count(n):
            Order.objects.all().delete()
            for _ in range(n):
                place_order(self.u, [(self.p.pk, 1)])
                Product.objects.filter(pk=self.p.pk).update(items_available=100)
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(reverse("catalog:my-orders"))
            return len(ctx.captured_queries)

        Product.objects.filter(pk=self.p.pk).update(items_available=100)
        self.assertEqual(count(2), count(8))


class OrderAdminTests(TestCase):
    def setUp(self):
        t = build_tree()
        self.order = place_order(user(), [(product("Buds", t["headphones"]).pk, 1)])
        admin = get_user_model().objects.create_superuser("admin", "a@example.com", "pass-for-tests-123")
        self.client.force_login(admin)

    def test_change_view_renders_read_only(self):
        response = self.client.get(reverse("admin:catalog_order_change", args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buds")
        self.assertNotContains(response, 'name="_save"')

    def test_add_and_delete_denied(self):
        self.assertEqual(self.client.get(reverse("admin:catalog_order_add")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:catalog_order_delete", args=[self.order.pk])).status_code, 403)
        response = self.client.post(reverse("admin:catalog_order_change", args=[self.order.pk]), {"total_cents": 1})
        self.assertEqual(response.status_code, 403)
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.total_cents, 1)
