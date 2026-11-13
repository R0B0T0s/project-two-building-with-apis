"""The saved-entries API's write side: create, update, delete."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse

from rentals import tmdb
from rentals.models import Movie, SavedMovie
from rentals.tests.test_api import PRIVATE, PUBLIC, SHARED, APITestBase

User = get_user_model()

ALIEN_DETAILS = {
    "id": 348,
    "title": "Alien",
    "release_date": "1979-05-25",
    "overview": "During its return to the earth, commercial spaceship Nostromo...",
    "poster_path": "/vfrQk5IPloGg1v9Rzbh2Eg3VGyM.jpg",
    "genres": [{"id": 27, "name": "Horror"}, {"id": 878, "name": "Science Fiction"}],
}


class CreateTests(APITestBase):
    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_create_runs_the_save_flow_and_rental_rules(self, get_details):
        friend = User.objects.create_user("friend", password="x")
        self.client.force_login(self.me)

        response = self.client.post(
            self.list_url,
            {
                "tmdb_id": 348,
                "status": "rented",
                "rental_days": 7,
                "rating": 5,
                "notes": "Still terrifying.",
                "visibility": "shared",
                "shared_with": ["friend"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        get_details.assert_called_once_with(348)
        saved = SavedMovie.objects.get(owner=self.me)
        self.assertEqual(response.data["id"], saved.pk)
        self.assertEqual(saved.movie.title, "Alien")
        self.assertEqual(
            sorted(saved.movie.genres.values_list("name", flat=True)),
            ["Horror", "Science Fiction"],
        )
        self.assertEqual(saved.status, SavedMovie.Status.RENTED)
        self.assertIsNotNone(saved.rented_at)
        self.assertEqual(saved.due_at - saved.rented_at, timedelta(days=7))
        self.assertEqual(saved.rating, 5)
        self.assertEqual(saved.notes, "Still terrifying.")
        self.assertEqual(saved.visibility, SavedMovie.Visibility.SHARED)
        self.assertEqual(list(saved.shared_with.all()), [friend])
        self.assertEqual(response.data["movie"]["title"], "Alien")
        self.assertNotIn("rental_days", response.data)
        self.assertNotIn("tmdb_id", response.data)

    @patch(
        "rentals.tmdb.get_movie_details",
        side_effect=tmdb.TMDBUnavailable("timed out", unreachable=True),
    )
    def test_tmdb_failure_on_create_is_503_and_saves_nothing(self, get_details):
        self.client.force_login(self.me)

        response = self.client.post(
            self.list_url,
            {"tmdb_id": 348, "status": "rented", "notes": "Can't wait"},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("TMDB", response.data["detail"])
        self.assertIn("wasn't saved", response.data["detail"])
        self.assertFalse(Movie.objects.exists())
        self.assertFalse(SavedMovie.objects.exists())


class EditPermissionTests(APITestBase):
    """The edit side of the matrix: who may update and delete each entry.

    Owner and staff may write. Anyone else gets 404 (even if they can view
    the entry), and signed-out callers get 401.
    """

    def test_update_and_delete_follow_the_edit_rule(self):
        friend = User.objects.create_user("friend", password="x")
        employee = User.objects.create_user("employee", password="x", is_staff=True)
        admin = User.objects.create_superuser("admin", password="x")
        callers = {
            "owner": (self.me, 200, 204),
            "employee": (employee, 200, 204),
            "admin": (admin, 200, 204),
            "other user": (self.other, 404, 404),
            "shared-with user": (friend, 404, 404),
            "signed out": (None, 401, 401),
        }

        for visibility in [PRIVATE, PUBLIC, SHARED]:
            for name, (caller, update_status, delete_status) in callers.items():
                with self.subTest(visibility=visibility, caller=name):
                    saved = self.save(
                        self.me, "Entry", visibility=visibility, shared_with=[friend]
                    )
                    url = reverse("api:saved-detail", args=[saved.pk])
                    self.client.logout()
                    if caller:
                        self.client.force_login(caller)

                    response = self.client.patch(
                        url, {"notes": f"by {name}"}, format="json"
                    )
                    self.assertEqual(response.status_code, update_status)
                    saved.refresh_from_db()
                    if update_status == 200:
                        self.assertEqual(saved.notes, f"by {name}")
                        self.assertEqual(saved.owner, self.me)
                    else:
                        self.assertEqual(saved.notes, "")

                    response = self.client.delete(url)
                    self.assertEqual(response.status_code, delete_status)
                    self.assertEqual(
                        SavedMovie.objects.filter(pk=saved.pk).exists(),
                        delete_status != 204,
                    )
                    saved.delete()


class CreateValidationTests(APITestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.me)

    def post(self, data):
        return self.client.post(self.list_url, data, format="json")

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_tmdb_id_alone_creates_with_the_defaults(self, get_details):
        response = self.post({"tmdb_id": 348})

        self.assertEqual(response.status_code, 201, response.data)
        saved = SavedMovie.objects.get(owner=self.me)
        self.assertEqual(saved.status, SavedMovie.Status.WANT_TO_RENT)
        self.assertEqual(saved.visibility, SavedMovie.Visibility.PRIVATE)
        self.assertIsNone(saved.rented_at)
        self.assertIsNone(saved.due_at)
        self.assertIsNone(saved.rating)

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_rented_without_rental_days_defaults_to_two_days(self, get_details):
        response = self.post({"tmdb_id": 348, "status": "rented"})

        self.assertEqual(response.status_code, 201, response.data)
        saved = SavedMovie.objects.get(owner=self.me)
        self.assertEqual(saved.due_at - saved.rented_at, timedelta(days=2))

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_duplicate_create_is_a_validation_error(self, get_details):
        self.assertEqual(self.post({"tmdb_id": 348}).status_code, 201)
        get_details.reset_mock()

        response = self.post({"tmdb_id": 348, "notes": "again"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("already in your library", str(response.data["tmdb_id"]))
        self.assertEqual(SavedMovie.objects.filter(owner=self.me).count(), 1)
        get_details.assert_not_called()

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_another_user_can_save_the_same_movie(self, get_details):
        self.assertEqual(self.post({"tmdb_id": 348}).status_code, 201)
        self.client.force_login(self.other)

        self.assertEqual(self.post({"tmdb_id": 348}).status_code, 201)
        self.assertEqual(Movie.objects.count(), 1)

    @patch("rentals.tmdb.get_movie_details")
    def test_missing_tmdb_id_is_a_validation_error(self, get_details):
        response = self.post({"notes": "No movie"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("tmdb_id", response.data)
        get_details.assert_not_called()

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_bad_values_are_validation_errors_and_save_nothing(self, get_details):
        cases = {
            "rental_days": {"tmdb_id": 348, "status": "rented", "rental_days": 3},
            "rating": {"tmdb_id": 348, "rating": 6},
            "status": {"tmdb_id": 348, "status": "lost"},
            "visibility": {"tmdb_id": 348, "visibility": "secret"},
        }
        for field, data in cases.items():
            with self.subTest(field=field):
                response = self.post(data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)
        self.assertFalse(SavedMovie.objects.exists())
        get_details.assert_not_called()

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_unknown_username_is_a_validation_error(self, get_details):
        response = self.post(
            {"tmdb_id": 348, "visibility": "shared", "shared_with": ["nobody"]}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("No user with the username nobody", str(response.data))
        self.assertFalse(SavedMovie.objects.exists())

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_shared_needs_at_least_one_username(self, get_details):
        response = self.post({"tmdb_id": 348, "visibility": "shared"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("at least one username", str(response.data["shared_with"]))
        self.assertFalse(SavedMovie.objects.exists())

    @patch(
        "rentals.tmdb.get_movie_details",
        side_effect=tmdb.TMDBUnavailable("HTTP 429"),
    )
    def test_other_tmdb_failures_get_the_generic_503_message(self, get_details):
        response = self.post({"tmdb_id": 348})

        self.assertEqual(response.status_code, 503)
        self.assertIn("temporarily unavailable", response.data["detail"])
        self.assertNotIn("429", response.data["detail"])
        self.assertFalse(SavedMovie.objects.exists())


class UpdateTests(APITestBase):
    def setUp(self):
        super().setUp()
        self.saved = self.save(self.me, "Alien")
        self.url = reverse("api:saved-detail", args=[self.saved.pk])
        self.client.force_login(self.me)

    def patch_entry(self, data):
        response = self.client.patch(self.url, data, format="json")
        self.saved.refresh_from_db()
        return response

    @patch("rentals.tmdb.get_movie_details")
    def test_tmdb_id_on_update_does_not_change_the_movie(self, get_details):
        movie = self.saved.movie
        other_movie = self.save(self.other, "Other").movie

        response = self.patch_entry(
            {"tmdb_id": other_movie.tmdb_id, "notes": "Still Alien"}
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.saved.movie, movie)
        self.assertEqual(self.saved.notes, "Still Alien")
        self.assertEqual(response.data["movie"]["tmdb_id"], movie.tmdb_id)
        get_details.assert_not_called()

    def test_rental_rules_on_update(self):
        response = self.patch_entry({"status": "rented", "rental_days": 1})
        self.assertEqual(response.status_code, 200, response.data)
        rented_at = self.saved.rented_at
        self.assertEqual(self.saved.due_at - rented_at, timedelta(days=1))

        # A notes-only edit leaves the rental alone.
        due_at = self.saved.due_at
        self.patch_entry({"notes": "Halfway through"})
        self.assertEqual(self.saved.due_at, due_at)

        # A new length on a current rental moves the due date, keeps the start.
        self.patch_entry({"rental_days": 7})
        self.assertEqual(self.saved.rented_at, rented_at)
        self.assertEqual(self.saved.due_at - rented_at, timedelta(days=7))

        # Ending the rental clears the due date and keeps "last rented".
        self.patch_entry({"status": "watched", "rating": 4})
        self.assertIsNone(self.saved.due_at)
        self.assertEqual(self.saved.rented_at, rented_at)
        self.assertEqual(self.saved.rating, 4)

        # Re-renting from Watched starts a fresh rental (default 2 days).
        self.patch_entry({"status": "rented"})
        self.assertGreater(self.saved.rented_at, rented_at)
        self.assertEqual(self.saved.due_at - self.saved.rented_at, timedelta(days=2))

    def test_full_update_with_put(self):
        friend = User.objects.create_user("friend", password="x")

        response = self.client.put(
            self.url,
            {
                "status": "watched",
                "rating": 3,
                "notes": "Good",
                "visibility": "shared",
                "shared_with": ["friend"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.status, SavedMovie.Status.WATCHED)
        self.assertEqual(self.saved.rating, 3)
        self.assertEqual(list(self.saved.shared_with.all()), [friend])
        self.assertEqual(response.data["shared_with"], ["friend"])

    def test_sharing_rules_on_update(self):
        friend = User.objects.create_user("friend", password="x")

        response = self.patch_entry({"visibility": "shared"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.saved.visibility, SavedMovie.Visibility.PRIVATE)

        response = self.patch_entry({"shared_with": ["nobody"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("No user with the username nobody", str(response.data))

        response = self.patch_entry({"visibility": "shared", "shared_with": ["friend"]})
        self.assertEqual(response.status_code, 200, response.data)
        # Already shared with someone: changing only the notes is fine.
        self.assertEqual(self.patch_entry({"notes": "Shared note"}).status_code, 200)
        # Emptying the list of a Shared entry is not.
        self.assertEqual(self.patch_entry({"shared_with": []}).status_code, 400)
        self.assertEqual(list(self.saved.shared_with.all()), [friend])

    def test_read_only_fields_are_ignored(self):
        response = self.patch_entry(
            {"due_at": "2000-01-01T00:00:00Z", "owner": "other", "id": 999}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.saved.due_at)
        self.assertEqual(self.saved.owner, self.me)
        self.assertEqual(self.saved.pk, response.data["id"])
