from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rentals.models import Movie, SavedMovie

User = get_user_model()


def edit_data(**overrides):
    data = {"status": "want", "rental_days": "2", "rating": "", "notes": ""}
    data.update(overrides)
    return data


class EditDeleteAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x")
        self.other = User.objects.create_user("other", password="x")
        self.employee = User.objects.create_user(
            "employee", password="x", is_staff=True
        )
        self.admin = User.objects.create_superuser("admin", password="x")
        movie = Movie.objects.create(
            tmdb_id=348, title="Alien", fetched_at=timezone.now()
        )
        # Public, so the other user can *view* it but still must not edit it.
        self.saved = SavedMovie.objects.create(
            owner=self.owner, movie=movie, visibility=SavedMovie.Visibility.PUBLIC
        )
        self.edit_url = reverse("rentals:saved_edit", args=[self.saved.pk])
        self.delete_url = reverse("rentals:saved_delete", args=[self.saved.pk])

    def test_only_owner_and_staff_can_edit(self):
        cases = [
            ("owner", self.owner, True),
            ("employee", self.employee, True),
            ("admin", self.admin, True),
            ("other user", self.other, False),
        ]
        for label, user, allowed in cases:
            with self.subTest(label):
                self.client.force_login(user)
                expected = 200 if allowed else 404
                self.assertEqual(self.client.get(self.edit_url).status_code, expected)
                self.assertEqual(self.client.get(self.delete_url).status_code, expected)

                response = self.client.post(
                    self.edit_url, edit_data(notes=f"by {label}")
                )
                self.saved.refresh_from_db()
                if allowed:
                    self.assertRedirects(response, self.saved.get_absolute_url())
                    self.assertEqual(self.saved.notes, f"by {label}")
                else:
                    self.assertEqual(response.status_code, 404)
                    self.assertNotEqual(self.saved.notes, f"by {label}")

    def test_signed_out_visitor_is_sent_to_login(self):
        for url in (self.edit_url, self.delete_url):
            with self.subTest(url):
                response = self.client.post(url, edit_data(notes="anonymous"))
                self.assertRedirects(
                    response, f"{reverse('accounts:login')}?next={url}"
                )
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.notes, "")

    def test_only_owner_or_staff_can_delete(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.delete_url).status_code, 404)
        self.assertTrue(SavedMovie.objects.filter(pk=self.saved.pk).exists())

        self.client.force_login(self.owner)
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, reverse("rentals:library"))
        self.assertFalse(SavedMovie.objects.filter(pk=self.saved.pk).exists())


class EditFormTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x")
        movie = Movie.objects.create(
            tmdb_id=348, title="Alien", fetched_at=timezone.now()
        )
        self.saved = SavedMovie.objects.create(owner=self.owner, movie=movie)
        self.url = reverse("rentals:saved_edit", args=[self.saved.pk])
        self.client.force_login(self.owner)

    def test_rating_accepts_only_empty_or_whole_numbers_1_to_5(self):
        for status in ("want", "rented", "watched"):
            for rating, valid in [
                ("", True),
                ("1", True),
                ("5", True),
                ("0", False),
                ("6", False),
                ("3.5", False),
                ("abc", False),
            ]:
                with self.subTest(status=status, rating=rating):
                    response = self.client.post(
                        self.url, edit_data(status=status, rating=rating)
                    )
                    self.saved.refresh_from_db()
                    if valid:
                        self.assertEqual(response.status_code, 302)
                        self.assertEqual(
                            self.saved.rating, int(rating) if rating else None
                        )
                    else:
                        self.assertEqual(response.status_code, 200)
                        self.assertTrue(response.context["form"].errors["rating"])

    def test_renting_uses_chosen_length_and_notes_edit_keeps_the_rental(self):
        self.client.post(self.url, edit_data(status="rented", rental_days="7"))
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.status, "rented")
        self.assertEqual((self.saved.due_at - self.saved.rented_at).days, 7)
        rented_at, due_at = self.saved.rented_at, self.saved.due_at

        # Still Rented, only the notes change: the rental is not restarted.
        self.client.post(
            self.url, edit_data(status="rented", rental_days="7", notes="Great")
        )
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.notes, "Great")
        self.assertEqual((self.saved.rented_at, self.saved.due_at), (rented_at, due_at))

        # Leaving Rented clears the due date and keeps "last rented".
        self.client.post(self.url, edit_data(status="watched"))
        self.saved.refresh_from_db()
        self.assertIsNone(self.saved.due_at)
        self.assertEqual(self.saved.rented_at, rented_at)

    def test_rental_length_must_be_1_2_or_7(self):
        response = self.client.post(
            self.url, edit_data(status="rented", rental_days="3")
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["rental_days"])
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.status, "want")


class CardActionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x")
        self.other = User.objects.create_user("other", password="x")
        movie = Movie.objects.create(
            tmdb_id=348, title="Alien", fetched_at=timezone.now()
        )
        self.saved = SavedMovie.objects.create(
            owner=self.owner, movie=movie, visibility=SavedMovie.Visibility.PUBLIC
        )
        self.rent_url = reverse("rentals:saved_rent", args=[self.saved.pk])
        self.watched_url = reverse("rentals:saved_watched", args=[self.saved.pk])

    def test_rent_then_mark_watched_in_one_click_each(self):
        self.client.force_login(self.owner)
        library = self.client.get(reverse("rentals:library"))
        self.assertContains(library, self.rent_url)
        self.assertContains(
            library, reverse("rentals:saved_edit", args=[self.saved.pk])
        )

        response = self.client.post(self.rent_url)
        self.assertRedirects(response, reverse("rentals:library"))
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.status, "rented")
        self.assertEqual((self.saved.due_at - self.saved.rented_at).days, 2)

        library = self.client.get(reverse("rentals:library"))
        self.assertContains(library, self.watched_url)
        self.assertContains(library, 'data-testid="due-on"')

        response = self.client.post(self.watched_url)
        self.assertRedirects(response, reverse("rentals:library"))
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.status, "watched")
        self.assertIsNone(self.saved.due_at)

    def test_actions_need_post_and_the_owner(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.rent_url).status_code, 405)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.rent_url).status_code, 404)
        self.assertEqual(self.client.post(self.watched_url).status_code, 404)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.status, "want")

    def test_overdue_badge_on_card_and_detail_page(self):
        past = timezone.now() - timedelta(days=3)
        self.saved.status, self.saved.rented_at = "rented", past
        self.saved.due_at = past + timedelta(days=1)
        self.saved.save()
        self.client.force_login(self.owner)
        self.assertContains(
            self.client.get(reverse("rentals:library")), 'data-testid="overdue-badge"'
        )
        self.assertContains(
            self.client.get(self.saved.get_absolute_url()),
            'data-testid="overdue-badge"',
        )


class DetailControlsTests(TestCase):
    def test_edit_and_delete_controls_only_for_owner_and_staff(self):
        owner = User.objects.create_user("owner", password="x")
        movie = Movie.objects.create(
            tmdb_id=348, title="Alien", fetched_at=timezone.now()
        )
        saved = SavedMovie.objects.create(
            owner=owner, movie=movie, visibility=SavedMovie.Visibility.PUBLIC
        )
        cases = [
            ("owner", owner, True),
            (
                "employee",
                User.objects.create_user("emp", password="x", is_staff=True),
                True,
            ),
            ("admin", User.objects.create_superuser("admin", password="x"), True),
            ("other user", User.objects.create_user("other", password="x"), False),
            ("signed out", None, False),
        ]
        for label, user, shown in cases:
            with self.subTest(label):
                self.client.logout()
                if user:
                    self.client.force_login(user)
                response = self.client.get(saved.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                if shown:
                    self.assertContains(response, 'data-testid="owner-controls"')
                else:
                    self.assertNotContains(response, 'data-testid="owner-controls"')
                    self.assertNotContains(
                        response, reverse("rentals:saved_edit", args=[saved.pk])
                    )


class ChangeRentalLengthTests(TestCase):
    def test_changing_length_of_a_current_rental_moves_the_due_date(self):
        owner = User.objects.create_user("owner", password="x")
        movie = Movie.objects.create(
            tmdb_id=348, title="Alien", fetched_at=timezone.now()
        )
        saved = SavedMovie.objects.create(owner=owner, movie=movie)
        saved.change_status(SavedMovie.Status.RENTED, rental_days=2)
        saved.save()
        rented_at = saved.rented_at
        url = reverse("rentals:saved_edit", args=[saved.pk])
        self.client.force_login(owner)

        # The form opens on the current rental's length, not the 2-day default.
        saved.due_at = rented_at + timedelta(days=7)
        saved.save()
        form = self.client.get(url).context["form"]
        self.assertEqual(form["rental_days"].value(), 7)

        # Still Rented, length changed to 1: due date is recalculated from the
        # original start, and the start date is kept.
        self.client.post(url, edit_data(status="rented", rental_days="1"))
        saved.refresh_from_db()
        self.assertEqual(saved.rented_at, rented_at)
        self.assertEqual(saved.due_at, rented_at + timedelta(days=1))
