"""Spec: accounts (sign-up with email as the username, login by email)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Order
from catalog.tests.factories import build_tree, product, user

User = get_user_model()
SIGNUP = reverse("signup")
HOME = reverse("catalog:product-list")
PASSWORD = "a-good-pass-phrase-77"


def signup_data(email="new@example.com", password=PASSWORD, repeat=None, **extra):
    return {"email": email, "password1": password, "password2": password if repeat is None else repeat, **extra}


class SignUpTests(TestCase):
    def test_page_renders_for_anonymous(self):
        response = self.client.get(SIGNUP)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create an account")

    def test_successful_signup_logs_in_and_header_shows_email(self):
        response = self.client.post(SIGNUP, signup_data())
        self.assertRedirects(response, HOME)
        self.assertEqual(User.objects.get().username, "new@example.com")
        self.assertContains(self.client.get(HOME), "Signed in as <strong>new@example.com</strong>", html=False)

    def test_new_account_is_not_staff_and_cannot_use_admin(self):
        self.client.post(SIGNUP, signup_data())
        new = User.objects.get(username="new@example.com")
        self.assertFalse(new.is_staff or new.is_superuser)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_logged_in_user_is_redirected_home(self):
        self.client.force_login(user())
        self.assertRedirects(self.client.get(SIGNUP), HOME)
        self.assertRedirects(self.client.post(SIGNUP, signup_data()), HOME)
        self.assertEqual(User.objects.count(), 1)

    def test_username_and_email_stored_lower_case(self):
        self.client.post(SIGNUP, signup_data(email="Ann@Example.com"))
        new = User.objects.get()
        self.assertEqual((new.username, new.email), ("ann@example.com", "ann@example.com"))

    def test_duplicate_email_ignoring_case(self):
        user("shopper@example.com", email="shopper@example.com")
        response = self.client.post(SIGNUP, signup_data(email="SHOPPER@example.com"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_of_a_mixed_case_username_is_also_rejected(self):
        user("Legacy@Example.com")
        response = self.client.post(SIGNUP, signup_data(email="legacy@example.com"))
        self.assertContains(response, "already registered")
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_email(self):
        response = self.client.post(SIGNUP, signup_data(email="not-an-email"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_passwords_differ(self):
        response = self.client.post(SIGNUP, signup_data(repeat="something-else-entirely-1"))
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_weak_password(self):
        response = self.client.post(SIGNUP, signup_data(password="12345678"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("password1", response.context["form"].errors)
        self.assertContains(response, "entirely numeric")
        self.assertFalse(User.objects.exists())

    def test_password_too_similar_to_email(self):
        response = self.client.post(SIGNUP, signup_data(email="johnsmith@example.com", password="johnsmith@example"))
        self.assertIn("password1", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_missing_fields(self):
        response = self.client.post(SIGNUP, {})
        self.assertEqual(set(response.context["form"].errors), {"email", "password1", "password2"})

    def test_sign_up_without_csrf_token_is_403(self):
        from django.test import Client

        response = Client(enforce_csrf_checks=True).post(SIGNUP, signup_data())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.exists())


class ReturnTargetTests(TestCase):
    def setUp(self):
        t = build_tree()
        self.p = product("Buds", t["headphones"], items_available=3)

    def test_signup_from_a_buy_redirect_returns_to_the_product_page_without_an_order(self):
        page = reverse("catalog:product-detail", args=[self.p.slug])
        response = self.client.get(page)
        buy_link = f'{reverse("login")}?next={page}'
        self.assertContains(response, f'href="{buy_link}"', html=False)
        login_page = self.client.get(buy_link)
        self.assertContains(login_page, f'href="{SIGNUP}?next={page}"', html=False)
        signup_page = self.client.get(f"{SIGNUP}?next={page}")
        self.assertContains(signup_page, f'href="{reverse("login")}?next={page}"', html=False)
        self.assertContains(signup_page, f'name="next" value="{page}"', html=False)
        response = self.client.post(SIGNUP, signup_data(next=page))
        self.assertRedirects(response, page)
        self.assertFalse(Order.objects.exists())
        self.p.refresh_from_db()
        self.assertEqual(self.p.items_available, 3)

    def test_signup_keeps_a_filtered_listing_url(self):
        target = f"{HOME}?q=buds&price_max=5000"
        response = self.client.post(SIGNUP, signup_data(next=target))
        self.assertRedirects(response, target)

    def test_external_next_goes_home(self):
        response = self.client.post(SIGNUP, signup_data(next="https://evil.example"))
        self.assertRedirects(response, HOME, fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 1)

    def test_next_survives_a_failed_submit(self):
        page = reverse("catalog:product-detail", args=[self.p.slug])
        response = self.client.post(SIGNUP, signup_data(email="bad", next=page))
        self.assertContains(response, f'name="next" value="{page}"', html=False)

    def test_login_page_without_next_links_to_plain_signup(self):
        self.assertContains(self.client.get(reverse("login")), f'href="{SIGNUP}"', html=False)


class EmailLoginTests(TestCase):
    def setUp(self):
        user("shopper@example.com", PASSWORD, email="shopper@example.com")

    def login(self, username, password=PASSWORD, **extra):
        return self.client.post(reverse("login"), {"username": username, "password": password, **extra})

    def test_login_form_is_labelled_email(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, ">Email<")
        self.assertNotContains(response, ">Username<")

    def test_mixed_case_email_logs_in(self):
        response = self.login("Shopper@Example.com", next=HOME)
        self.assertRedirects(response, HOME)
        self.assertContains(self.client.get(HOME), "Signed in as <strong>shopper@example.com</strong>", html=False)

    def test_wrong_password_shows_generic_error(self):
        response = self.login("shopper@example.com", "wrong-password-1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "match")
        self.assertNotContains(response, "Invalid password")
        self.assertNotContains(response, "No such")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_email_gets_the_same_error(self):
        wrong_pass = self.login("shopper@example.com", "wrong-password-1").content.decode()
        unknown = self.login("nobody@example.com").content.decode()
        message = "Your email and password"
        self.assertIn(message, wrong_pass)
        self.assertIn(message, unknown)

    def test_signed_up_user_can_log_in_again(self):
        self.client.post(SIGNUP, signup_data(email="Ann@Example.com"))
        self.client.post(reverse("logout"))
        self.assertRedirects(self.login("ANN@example.COM"), HOME, fetch_redirect_response=False)

    def test_non_email_username_still_logs_in_by_exact_match(self):
        user("legacy", PASSWORD)
        self.assertRedirects(self.login("legacy"), HOME, fetch_redirect_response=False)
