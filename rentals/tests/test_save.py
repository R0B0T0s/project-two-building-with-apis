from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from rentals import services, tmdb
from rentals.models import Movie, SavedMovie

User = get_user_model()

ALIEN_DETAILS = {
    "id": 348,
    "title": "Alien",
    "release_date": "1979-05-25",
    "overview": "During its return to the earth, commercial spaceship Nostromo...",
    "poster_path": "/vfrQk5IPloGg1v9Rzbh2Eg3VGyM.jpg",
    "genres": [{"id": 27, "name": "Horror"}, {"id": 878, "name": "Science Fiction"}],
}


class SaveFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("moviefan", password="x")

    @patch("rentals.tmdb.get_movie_details")
    def test_fresh_movie_is_reused_and_stale_or_missing_movie_is_fetched(
        self, get_details
    ):
        get_details.return_value = ALIEN_DETAILS

        with self.subTest("missing movie is fetched and stored locally"):
            saved = services.save_movie(self.user, 348)

            get_details.assert_called_once_with(348)
            movie = Movie.objects.get(tmdb_id=348)
            self.assertEqual(saved.movie, movie)
            self.assertEqual(movie.title, "Alien")
            self.assertEqual(movie.release_year, 1979)
            self.assertEqual(movie.overview, ALIEN_DETAILS["overview"])
            self.assertEqual(movie.poster_path, "/vfrQk5IPloGg1v9Rzbh2Eg3VGyM.jpg")
            self.assertEqual(
                sorted(movie.genres.values_list("name", flat=True)),
                ["Horror", "Science Fiction"],
            )

        with self.subTest("movie fetched under six months ago is reused"):
            get_details.reset_mock()
            Movie.objects.filter(tmdb_id=348).update(
                title="Local copy", fetched_at=timezone.now() - timedelta(days=150)
            )
            other = User.objects.create_user("friend", password="x")

            saved = services.save_movie(other, 348)

            get_details.assert_not_called()
            self.assertEqual(saved.movie.title, "Local copy")

        with self.subTest("movie fetched over six months ago is fetched again"):
            Movie.objects.filter(tmdb_id=348).update(
                fetched_at=timezone.now() - timedelta(days=200)
            )
            third = User.objects.create_user("third", password="x")

            saved = services.save_movie(third, 348)

            get_details.assert_called_once_with(348)
            self.assertEqual(saved.movie.title, "Alien")
            self.assertEqual(Movie.objects.count(), 1)
            self.assertEqual(SavedMovie.objects.count(), 3)


class SaveViewTMDBFailureTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("moviefan", password="x"))
        # Report server errors as responses (as a browser sees them), not exceptions.
        self.client.raise_request_exception = False

    @patch("rentals.tmdb.search_movies")
    @patch("rentals.tmdb.get_movie_details")
    def test_tmdb_failure_saves_nothing_and_shows_error(self, get_details, search):
        search.return_value = {"results": [], "page": 2, "total_pages": 2}
        get_details.side_effect = tmdb.TMDBUnavailable(
            "TECHNICAL-DETAIL status 503", unreachable=False
        )

        response = self.client.post(
            reverse("rentals:save"),
            {"tmdb_id": "348", "q": "alien", "page": "2"},
            follow=True,
        )

        self.assertRedirects(response, f"{reverse('rentals:find')}?q=alien&page=2")
        self.assertEqual(Movie.objects.count(), 0)
        self.assertEqual(SavedMovie.objects.count(), 0)
        self.assertContains(response, 'class="alert alert-danger')
        self.assertContains(response, escape("wasn't saved"))
        self.assertNotContains(response, "TECHNICAL-DETAIL")


class SaveFlowDuplicateAndDefaultsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("moviefan", password="x")

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_new_entry_defaults_to_want_to_rent_and_private(self, get_details):
        saved = services.save_movie(self.user, 348)

        self.assertEqual(saved.owner, self.user)
        self.assertEqual(saved.status, SavedMovie.Status.WANT_TO_RENT)
        self.assertEqual(saved.visibility, SavedMovie.Visibility.PRIVATE)
        self.assertIsNone(saved.rating)
        self.assertIsNone(saved.rented_at)
        self.assertIsNone(saved.due_at)
        self.assertEqual(saved.notes, "")
        self.assertFalse(saved.shared_with.exists())

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_duplicate_save_raises_already_saved_without_calling_tmdb(
        self, get_details
    ):
        first = services.save_movie(self.user, 348)
        # Make the movie stale, so only the duplicate check can avoid a fetch.
        Movie.objects.update(fetched_at=timezone.now() - timedelta(days=365))
        get_details.reset_mock()

        with self.assertRaises(services.AlreadySaved) as caught:
            services.save_movie(self.user, "348")

        self.assertEqual(caught.exception.saved_movie, first)
        get_details.assert_not_called()
        self.assertEqual(SavedMovie.objects.count(), 1)

    def test_unique_constraint_blocks_second_entry_for_same_owner_and_movie(self):
        movie = Movie.objects.create(tmdb_id=1, title="X", fetched_at=timezone.now())
        SavedMovie.objects.create(owner=self.user, movie=movie)

        with self.assertRaises(IntegrityError):
            SavedMovie.objects.create(owner=self.user, movie=movie)

    def test_rating_outside_1_to_5_is_rejected_by_database(self):
        movie = Movie.objects.create(tmdb_id=1, title="X", fetched_at=timezone.now())

        with self.assertRaises(IntegrityError):
            SavedMovie.objects.create(owner=self.user, movie=movie, rating=6)

    @patch("rentals.tmdb.get_movie_details")
    def test_missing_release_date_and_poster_are_stored_as_empty(self, get_details):
        get_details.return_value = {"id": 9, "title": "Lost Film", "release_date": ""}

        saved = services.save_movie(self.user, 9)

        self.assertIsNone(saved.movie.release_year)
        self.assertEqual(saved.movie.poster_path, "")
        self.assertFalse(saved.movie.genres.exists())


NO_RESULTS = {"results": [], "page": 1, "total_pages": 1}


@patch("rentals.tmdb.search_movies", return_value=NO_RESULTS)
class SaveViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("moviefan", password="x")
        self.client.force_login(self.user)

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_save_returns_to_same_results_with_confirmation_and_edit_link(
        self, get_details, search
    ):
        response = self.client.post(
            reverse("rentals:save"),
            {"tmdb_id": "348", "q": "alien", "page": "3"},
            follow=True,
        )

        saved = SavedMovie.objects.get(owner=self.user)
        self.assertRedirects(response, f"{reverse('rentals:find')}?q=alien&page=3")
        self.assertContains(response, 'class="alert alert-success')
        self.assertContains(response, "Saved <strong>Alien</strong> to your library.")
        self.assertContains(
            response,
            f'<a href="{saved.get_absolute_url()}" class="alert-link">Edit details</a>',
        )

    @patch("rentals.tmdb.get_movie_details", return_value=ALIEN_DETAILS)
    def test_duplicate_save_shows_already_in_library_and_keeps_one_entry(
        self, get_details, search
    ):
        url = reverse("rentals:save")
        self.client.post(url, {"tmdb_id": "348", "q": "alien"})

        response = self.client.post(url, {"tmdb_id": "348", "q": "alien"}, follow=True)

        self.assertEqual(SavedMovie.objects.count(), 1)
        self.assertContains(response, 'class="alert alert-info')
        self.assertContains(response, "is already in your library")

    @patch("rentals.tmdb.get_movie_details")
    def test_unreachable_tmdb_shows_couldnt_reach_message(self, get_details, search):
        get_details.side_effect = tmdb.TMDBUnavailable("timeout", unreachable=True)

        response = self.client.post(
            reverse("rentals:save"), {"tmdb_id": "348", "q": "alien"}, follow=True
        )

        self.assertContains(
            response, escape("Couldn't reach TMDB, so the movie wasn't saved.")
        )
        self.assertEqual(SavedMovie.objects.count(), 0)

    def test_save_requires_login_and_post(self, search):
        url = reverse("rentals:save")
        self.assertEqual(self.client.get(url).status_code, 405)

        self.client.logout()
        with patch("rentals.tmdb.get_movie_details") as get_details:
            response = self.client.post(url, {"tmdb_id": "348"})

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={url}",
            fetch_redirect_response=False,
        )
        get_details.assert_not_called()

    def test_invalid_tmdb_id_shows_error_and_saves_nothing(self, search):
        with patch("rentals.tmdb.get_movie_details") as get_details:
            response = self.client.post(
                reverse("rentals:save"), {"tmdb_id": "abc"}, follow=True
            )

        get_details.assert_not_called()
        self.assertRedirects(response, reverse("rentals:find"))
        self.assertContains(response, 'class="alert alert-danger')
        self.assertEqual(SavedMovie.objects.count(), 0)


class SavedDetailStubTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("moviefan", password="x")
        movie = Movie.objects.create(
            tmdb_id=348, title="Alien", fetched_at=timezone.now()
        )
        self.saved = SavedMovie.objects.create(owner=self.owner, movie=movie)

    def test_owner_and_staff_can_open_it_but_other_users_get_404(self):
        url = self.saved.get_absolute_url()
        cases = [
            ("owner", self.owner, 200),
            ("employee", User.objects.create_user("emp", is_staff=True), 200),
            ("admin", User.objects.create_superuser("boss"), 200),
            ("other user", User.objects.create_user("friend"), 404),
        ]
        for name, user, expected in cases:
            with self.subTest(name):
                self.client.force_login(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, expected)
                if expected == 200:
                    self.assertContains(response, "Alien")
                    self.assertContains(response, "Want to rent")
                    self.assertContains(response, "Private")
