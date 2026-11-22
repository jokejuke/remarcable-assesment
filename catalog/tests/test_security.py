"""Spec: web-security (CORS, CSRF, clickjacking, deployment check)."""

import os
import secrets
import subprocess
import sys
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from catalog.models import Category, Favorite, Order
from catalog.tests.factories import build_tree, product, user

BASE_DIR = Path(__file__).resolve().parents[2]
ORIGIN = "https://app.example.com"


@override_settings(CORS_ALLOWED_ORIGINS=[ORIGIN])
class CorsTests(TestCase):
    def test_allowed_origin_on_api(self):
        response = self.client.get("/api/products/", HTTP_ORIGIN=ORIGIN)
        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_unlisted_origin_gets_no_headers(self):
        response = self.client.get("/api/products/", HTTP_ORIGIN="https://evil.example")
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_storefront_path_gets_no_headers(self):
        response = self.client.get("/", HTTP_ORIGIN=ORIGIN)
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_preflight_does_not_allow_put(self):
        response = self.client.options(
            "/api/products/", HTTP_ORIGIN=ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="PUT",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization, content-type",
        )
        allowed = {m.strip() for m in response["Access-Control-Allow-Methods"].split(",")}
        self.assertEqual(allowed, {"GET", "HEAD", "OPTIONS", "POST", "DELETE"})
        self.assertEqual({h.strip() for h in response["Access-Control-Allow-Headers"].split(",")},
                         {"authorization", "content-type"})
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    @override_settings(CORS_ALLOWED_ORIGINS=[])
    def test_no_origins_configured_means_no_cors(self):
        response = self.client.get("/api/products/", HTTP_ORIGIN=ORIGIN)
        self.assertNotIn("Access-Control-Allow-Origin", response)


class CsrfTests(TestCase):
    def setUp(self):
        self.t = build_tree()
        self.p = product("Buds", self.t["headphones"])
        self.shopper = user("shopper")
        self.client = Client(enforce_csrf_checks=True)

    def test_buy_without_token_403(self):
        self.client.force_login(self.shopper)
        response = self.client.post(reverse("catalog:buy", args=[self.p.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Order.objects.exists())

    def test_api_favorite_write_without_token_403(self):
        self.client.force_login(self.shopper)
        self.assertEqual(self.client.post("/api/favorites/", {"product": self.p.pk}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/favorites/{self.p.pk}/").status_code, 403)
        self.assertFalse(Favorite.objects.exists())

    def test_login_without_token_403(self):
        response = self.client.post(reverse("login"), {"username": "shopper", "password": "pass-for-tests-123"})
        self.assertEqual(response.status_code, 403)

    def test_admin_save_without_token_403(self):
        admin = get_user_model().objects.create_superuser("admin", "a@example.com", "pass-for-tests-123")
        self.client.force_login(admin)
        url = reverse("admin:catalog_category_change", args=[self.t["fiction"].pk])
        response = self.client.post(url, {"name": "Changed", "parent": self.t["books"].pk, "kind": "products"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Category.objects.get(pk=self.t["fiction"].pk).name, "Fiction")

    def test_buy_with_token_works(self):
        self.client.force_login(self.shopper)
        self.client.get("/")  # sets the CSRF cookie
        token = self.client.cookies["csrftoken"].value
        response = self.client.post(reverse("catalog:buy", args=[self.p.pk]), {"csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.exists())


class HeaderTests(TestCase):
    def test_pages_forbid_framing(self):
        build_tree()
        for url in ("/", reverse("login"), "/api/docs/"):
            self.assertEqual(self.client.get(url)["X-Frame-Options"], "DENY", url)

    def test_nosniff(self):
        self.assertEqual(self.client.get("/")["X-Content-Type-Options"], "nosniff")


class DeployCheckTests(SimpleTestCase):
    def test_check_deploy_passes_with_production_env(self):
        env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "SYSTEMROOT"}}
        env.update(DEBUG="0", SECRET_KEY=secrets.token_urlsafe(60), ALLOWED_HOSTS="shop.example.com")
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
            cwd=BASE_DIR, env=env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no issues", result.stdout)
