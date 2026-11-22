"""Spec: api-auth (JWT and session authentication)."""

from datetime import timedelta

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from catalog.tests.factories import build_tree, product, user

PASSWORD = "pass-for-tests-123"


class JwtTests(APITestCase):
    def setUp(self):
        self.shopper = user("shopper@example.com", PASSWORD, email="shopper@example.com")

    def obtain(self, password=PASSWORD):
        return self.client.post("/api/auth/token/", {"email": "shopper@example.com", "password": password}, format="json")

    def test_valid_login_returns_pair(self):
        response = self.obtain()
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_wrong_password_401_no_tokens(self):
        response = self.obtain("nope")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access", response.data)

    def test_mixed_case_email_logs_in(self):
        response = self.client.post(
            "/api/auth/token/", {"email": "Shopper@Example.com", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_username_only_request_is_400(self):
        response = self.client.post(
            "/api/auth/token/", {"username": "shopper@example.com", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertNotIn("access", response.data)

    def test_unknown_email_401(self):
        response = self.client.post("/api/auth/token/", {"email": "nobody@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_bearer_token_authenticates(self):
        access = self.obtain().data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(self.client.get("/api/favorites/").status_code, 200)

    def test_expired_token_401(self):
        token = AccessToken.for_user(self.shopper)
        token.set_exp(lifetime=-timedelta(seconds=1))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/favorites/").status_code, 401)

    def test_invalid_token_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")
        self.assertEqual(self.client.get("/api/favorites/").status_code, 401)

    def test_default_access_lifetime_is_15_minutes(self):
        token = AccessToken(self.obtain().data["access"])
        self.assertEqual(token["exp"] - token["iat"], 15 * 60)

    def test_refresh_rotates_and_old_refresh_rejected(self):
        refresh = self.obtain().data["refresh"]
        first = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertIn("access", first.data)
        self.assertNotEqual(first.data["refresh"], refresh)
        again = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(again.status_code, 401)

    def test_refresh_after_logout_rejected(self):
        refresh = self.obtain().data["refresh"]
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json").status_code, 200)
        response = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_anonymous_gets_401_with_bearer_challenge(self):
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response["WWW-Authenticate"].startswith("Bearer"))


class SessionApiTests(APITestCase):
    def setUp(self):
        self.shopper = user("shopper", PASSWORD)
        self.p = product("Buds", build_tree()["headphones"])

    def test_session_reads_orders(self):
        self.client.login(username="shopper", password=PASSWORD)
        self.assertEqual(self.client.get("/api/orders/").status_code, 200)

    def test_session_post_without_csrf_is_403(self):
        client = APIClient(enforce_csrf_checks=True)
        client.login(username="shopper", password=PASSWORD)
        response = client.post("/api/favorites/", {"product": self.p.pk}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.shopper.favorites.exists())

    def test_bearer_post_needs_no_csrf(self):
        # Token clients are not cookie-based, so CSRF does not apply to them.
        client = APIClient(enforce_csrf_checks=True)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.shopper)}")
        self.assertEqual(client.post("/api/favorites/", {"product": self.p.pk}, format="json").status_code, 201)


class SessionLoginFormTests(APITestCase):
    """The storefront login form takes an email in any letter case (spec: accounts)."""

    def setUp(self):
        user("shopper@example.com", PASSWORD, email="shopper@example.com")

    def test_mixed_case_email_logs_in(self):
        response = self.client.post("/accounts/login/", {"username": "Shopper@Example.COM", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/api/favorites/").status_code, 200)  # the session works

    def test_wrong_password_shows_the_generic_error(self):
        response = self.client.post("/accounts/login/", {"username": "shopper@example.com", "password": "nope-nope-1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your email and password didn")
        self.assertEqual(self.client.get("/api/favorites/").status_code, 401)
