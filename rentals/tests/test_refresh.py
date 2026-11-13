import io
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from rentals import tmdb
from rentals.models import Genre, Movie, SavedMovie

User = get_user_model()


def details(tmdb_id, title, genres=()):
    return {
        "id": tmdb_id,
        "title": title,
        "release_date": "1979-05-25",
        "overview": f"{title} overview",
        "poster_path": f"/{tmdb_id}.jpg",
        "genres": [{"id": gid, "name": name} for gid, name in genres],
    }


class RefreshMoviesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("moviefan", password="x")
        self.horror = Genre.objects.create(tmdb_id=27, name="Horror")

    def make_movie(self, tmdb_id, title, age_days, saved=True):
        movie = Movie.objects.create(
            tmdb_id=tmdb_id,
            title=title,
            fetched_at=timezone.now() - timedelta(days=age_days),
        )
        movie.genres.add(self.horror)
        if saved:
            SavedMovie.objects.create(owner=self.user, movie=movie)
        return movie

    def run_command(self):
        out = io.StringIO()
        call_command("refresh_movies", stdout=out)
        return out.getvalue()

    @patch("rentals.tmdb.get_movie_details")
    def test_stale_movies_are_refreshed_and_fresh_movies_are_untouched(
        self, get_details
    ):
        stale = self.make_movie(348, "Old title", age_days=160)
        fresh = self.make_movie(603, "Fresh title", age_days=30)
        get_details.return_value = details(
            348, "Alien", genres=[(878, "Science Fiction")]
        )
        before = timezone.now()

        self.run_command()

        get_details.assert_called_once_with(348)
        stale.refresh_from_db()
        self.assertEqual(stale.title, "Alien")
        self.assertEqual(stale.overview, "Alien overview")
        self.assertEqual(stale.release_year, 1979)
        self.assertEqual(
            list(stale.genres.values_list("name", flat=True)), ["Science Fiction"]
        )
        self.assertGreaterEqual(stale.fetched_at, before)
        fresh_fetched_at = fresh.fetched_at
        fresh.refresh_from_db()
        self.assertEqual(fresh.title, "Fresh title")
        self.assertEqual(fresh.fetched_at, fresh_fetched_at)

    @patch("rentals.tmdb.get_movie_details")
    def test_tmdb_failure_keeps_existing_data_and_later_movies_still_refresh(
        self, get_details
    ):
        failing = self.make_movie(348, "Keep me", age_days=160)
        later = self.make_movie(603, "Old Matrix", age_days=170)
        original_fetched_at = failing.fetched_at

        def fake_details(tmdb_id):
            if tmdb_id == 348:
                raise tmdb.TMDBUnavailable("TMDB returned status 500")
            return details(603, "The Matrix")

        get_details.side_effect = fake_details

        with self.assertLogs("rentals", level="WARNING") as logs:
            self.run_command()

        failing.refresh_from_db()
        self.assertEqual(failing.title, "Keep me")
        self.assertEqual(failing.fetched_at, original_fetched_at)
        self.assertEqual(
            list(failing.genres.values_list("name", flat=True)), ["Horror"]
        )
        later.refresh_from_db()
        self.assertEqual(later.title, "The Matrix")
        self.assertTrue(any("348" in line for line in logs.output))

    @patch("rentals.tmdb.get_movie_details")
    def test_movies_with_no_saved_entries_are_deleted(self, get_details):
        kept = self.make_movie(348, "Alien", age_days=30)
        self.make_movie(603, "Nobody saved this", age_days=30, saved=False)
        self.make_movie(604, "Stale and unsaved", age_days=200, saved=False)
        get_details.return_value = details(604, "Stale and unsaved")

        self.run_command()

        self.assertEqual(list(Movie.objects.all()), [kept])
        self.assertTrue(Genre.objects.filter(pk=self.horror.pk).exists())
        get_details.assert_not_called()

    @patch("rentals.tmdb.get_movie_details")
    def test_output_with_unprintable_titles_does_not_crash_on_a_limited_console(
        self, get_details
    ):
        self.make_movie(348, "Old", age_days=160)
        self.make_movie(603, "Old too", age_days=160)

        def fake_details(tmdb_id):
            if tmdb_id == 348:
                return details(348, "千と千尋の神隠し ★")
            raise tmdb.TMDBUnavailable("TMDB returned status 500")

        get_details.side_effect = fake_details
        Movie.objects.filter(tmdb_id=603).update(title="Amélie ★")
        # A cp1252 stream, like a default Windows console, can't encode these.
        raw = io.BytesIO()
        console = io.TextIOWrapper(raw, encoding="cp1252")

        with self.assertLogs("rentals", level="WARNING"):
            call_command("refresh_movies", stdout=console)

        console.flush()
        output = raw.getvalue().decode("cp1252")
        self.assertIn("Refreshed: ???????? ? (1979)", output)
        self.assertIn("Amélie ?", output)
        self.assertIn("Refreshed 1, failed 1, deleted 0", output)
        self.assertEqual(Movie.objects.get(tmdb_id=348).title, "千と千尋の神隠し ★")
