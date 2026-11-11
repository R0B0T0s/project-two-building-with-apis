from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rentals.models import Genre, Movie, SavedMovie
from rentals.permissions import is_staff_user

User = get_user_model()


class StaffHelperTests(TestCase):
    def test_only_active_employees_and_admins_count_as_staff(self):
        cases = [
            ("signed-out visitor", AnonymousUser(), False),
            ("regular user", User.objects.create_user("user"), False),
            ("employee", User.objects.create_user("emp", is_staff=True), True),
            ("admin", User.objects.create_superuser("boss"), True),
            (
                "superuser without is_staff",
                User.objects.create_user("odd", is_superuser=True),
                True,
            ),
            (
                "deactivated employee",
                User.objects.create_user("gone", is_staff=True, is_active=False),
                False,
            ),
        ]
        for name, user, expected in cases:
            with self.subTest(name):
                self.assertIs(is_staff_user(user), expected)


class AdminSiteTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("boss", password="x")
        self.client.force_login(self.admin)
        genre = Genre.objects.create(tmdb_id=27, name="Horror")
        movie = Movie.objects.create(
            tmdb_id=348, title="Alien", fetched_at=timezone.now()
        )
        movie.genres.add(genre)
        self.saved = SavedMovie.objects.create(owner=self.admin, movie=movie)

    def test_admin_can_open_list_and_change_pages_for_all_three_models(self):
        for model, obj in [
            ("genre", Genre.objects.get()),
            ("movie", Movie.objects.get()),
            ("savedmovie", self.saved),
        ]:
            with self.subTest(model):
                changelist = reverse(f"admin:rentals_{model}_changelist")
                change = reverse(f"admin:rentals_{model}_change", args=[obj.pk])
                self.assertEqual(self.client.get(changelist).status_code, 200)
                self.assertContains(self.client.get(change), str(obj))

    def test_admin_can_mark_a_user_as_staff(self):
        user = User.objects.create_user("helper", password="x")
        joined = timezone.localtime(user.date_joined)

        response = self.client.post(
            reverse("admin:auth_user_change", args=[user.pk]),
            {
                "username": "helper",
                "is_active": "on",
                "is_staff": "on",
                "date_joined_0": joined.strftime("%Y-%m-%d"),
                "date_joined_1": joined.strftime("%H:%M:%S"),
            },
        )

        self.assertRedirects(response, reverse("admin:auth_user_changelist"))
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertTrue(is_staff_user(user))
