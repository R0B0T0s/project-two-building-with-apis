from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

PASSWORD = "Rent-a-movie-2026!"


class SignUpTests(TestCase):
    def test_sign_up_creates_account_and_signs_visitor_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {"username": "moviefan", "password1": PASSWORD, "password2": PASSWORD},
        )

        self.assertRedirects(response, reverse("rentals:home"))
        user = User.objects.get(username="moviefan")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(user.pk),
            "visitor should be signed in after signing up",
        )


class MyAccountAccessTests(TestCase):
    def setUp(self):
        # Report server errors as responses (as a browser sees them), not exceptions.
        self.client.raise_request_exception = False

    def test_signed_out_visitor_is_redirected_to_login(self):
        url = reverse("accounts:my_account")

        response = self.client.get(url)

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")


class MyAccountUpdateTests(TestCase):
    def test_saving_updates_name_and_email_only(self):
        user = User.objects.create_user(
            username="moviefan", password=PASSWORD, email="old@example.com"
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:my_account"),
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "username": "someone-else",
                "is_staff": "on",
            },
        )

        self.assertRedirects(response, reverse("accounts:my_account"))
        user.refresh_from_db()
        self.assertEqual(
            (user.first_name, user.last_name, user.email),
            ("Ada", "Lovelace", "ada@example.com"),
        )
        self.assertEqual(user.username, "moviefan")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password(PASSWORD))


class SignUpPageTests(TestCase):
    def test_sign_up_page_warns_that_username_is_public(self):
        response = self.client.get(reverse("accounts:signup"))

        self.assertContains(response, "Your username is shown publicly.")

    def test_mismatched_passwords_create_no_account(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {"username": "moviefan", "password1": PASSWORD, "password2": "different"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="moviefan").exists())
        self.assertNotIn("_auth_user_id", self.client.session)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="moviefan", password=PASSWORD)

    def test_login_with_correct_password_signs_user_in(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "moviefan", "password": PASSWORD}
        )

        self.assertRedirects(response, reverse("rentals:home"))
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.pk))

    def test_login_with_wrong_password_shows_error(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "moviefan", "password": "wrong"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_returns_to_next_page(self):
        my_account = reverse("accounts:my_account")

        response = self.client.post(
            f"{reverse('accounts:login')}?next={my_account}",
            {"username": "moviefan", "password": PASSWORD, "next": my_account},
        )

        self.assertRedirects(response, my_account)

    def test_logout_signs_user_out(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("rentals:home"))
        self.assertNotIn("_auth_user_id", self.client.session)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="moviefan", password=PASSWORD)

    def test_password_change_requires_login(self):
        url = reverse("accounts:password_change")

        response = self.client.get(url)

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    def test_user_can_change_password_and_stays_signed_in(self):
        self.client.force_login(self.user)
        new_password = "Brand-new-pass-2026!"

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )

        self.assertRedirects(response, reverse("accounts:password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.pk))

    def test_wrong_old_password_keeps_password(self):
        self.client.force_login(self.user)

        self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "wrong",
                "new_password1": "Brand-new-pass-2026!",
                "new_password2": "Brand-new-pass-2026!",
            },
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))


class NavbarTests(TestCase):
    def nav_of(self, response):
        html = response.content.decode()
        start, end = html.find("<nav"), html.find("</nav>")
        self.assertNotEqual(start, -1, "page has no <nav>")
        return html[start:end]

    def test_signed_out_navbar_shows_login_and_sign_up(self):
        nav = self.nav_of(self.client.get(reverse("rentals:home")))

        self.assertIn(f'href="{reverse("accounts:login")}"', nav)
        self.assertIn(f'href="{reverse("accounts:signup")}"', nav)
        self.assertNotIn("Log out", nav)

    def test_signed_in_navbar_shows_username_and_logout(self):
        user = User.objects.create_user(username="moviefan", password=PASSWORD)
        self.client.force_login(user)

        nav = self.nav_of(self.client.get(reverse("rentals:home")))

        self.assertIn("moviefan", nav)
        self.assertIn(f'href="{reverse("accounts:my_account")}"', nav)
        self.assertIn(f'action="{reverse("accounts:logout")}"', nav)
        self.assertNotIn(f'href="{reverse("accounts:signup")}"', nav)


class MyAccountPageTests(TestCase):
    def test_form_is_prefilled_with_current_details(self):
        user = User.objects.create_user(
            username="moviefan",
            password=PASSWORD,
            first_name="Ada",
            email="ada@example.com",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:my_account"))

        self.assertContains(response, 'value="Ada"')
        self.assertContains(response, 'value="ada@example.com"')

    def test_invalid_email_is_rejected(self):
        user = User.objects.create_user(
            username="moviefan", password=PASSWORD, email="ada@example.com"
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:my_account"),
            {"first_name": "", "last_name": "", "email": "not-an-email"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is-invalid")
        user.refresh_from_db()
        self.assertEqual(user.email, "ada@example.com")
