from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rentals.models import Genre, Movie, SavedMovie

User = get_user_model()


def make_movie(tmdb_id, title, **fields):
    return Movie.objects.create(
        tmdb_id=tmdb_id, title=title, fetched_at=timezone.now(), **fields
    )


class VisibleToTests(TestCase):
    def test_private_entry_is_visible_only_to_its_owner(self):
        owner = User.objects.create_user("owner", password="x")
        other = User.objects.create_user("other", password="x")
        saved = SavedMovie.objects.create(
            owner=owner, movie=make_movie(348, "Alien")
        )  # Private by default

        cases = [
            ("owner", owner, True),
            ("other user", other, False),
            ("signed out", AnonymousUser(), False),
        ]
        for label, viewer, expected in cases:
            with self.subTest(label):
                visible = SavedMovie.objects.visible_to(viewer)
                self.assertEqual(visible.filter(pk=saved.pk).exists(), expected)


class MyLibraryTests(TestCase):
    def test_lists_only_the_signed_in_users_entries(self):
        me = User.objects.create_user("me", password="x")
        other = User.objects.create_user("other", password="x")
        SavedMovie.objects.create(owner=me, movie=make_movie(348, "Alien"))
        SavedMovie.objects.create(owner=me, movie=make_movie(679, "Aliens"))
        SavedMovie.objects.create(
            owner=other,
            movie=make_movie(78, "Blade Runner"),
            visibility=SavedMovie.Visibility.PUBLIC,
        )
        self.client.force_login(me)

        response = self.client.get(reverse("rentals:library"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-testid="saved-card"', count=2)
        self.assertContains(response, "Alien")
        self.assertContains(response, "Aliens")
        self.assertNotContains(response, "Blade Runner")

    def test_requires_login(self):
        url = reverse("rentals:library")

        response = self.client.get(url)

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    @patch("rentals.tmdb.get_movie_details")
    @patch("rentals.tmdb.search_movies")
    def test_renders_from_local_data_without_calling_tmdb(
        self, search_movies, get_movie_details
    ):
        me = User.objects.create_user("me", password="x")
        SavedMovie.objects.create(owner=me, movie=make_movie(348, "Alien"))
        self.client.force_login(me)

        response = self.client.get(reverse("rentals:library"))

        self.assertContains(response, "Alien")
        search_movies.assert_not_called()
        get_movie_details.assert_not_called()

    def test_empty_library_shows_a_hint(self):
        self.client.force_login(User.objects.create_user("me", password="x"))

        response = self.client.get(reverse("rentals:library"))

        self.assertContains(response, 'data-testid="library-empty"')


CHICAGO = ZoneInfo("America/Chicago")


@patch("rentals.tmdb.get_movie_details")
@patch("rentals.tmdb.search_movies")
class SavedDetailTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x")
        movie = make_movie(
            348,
            "Alien",
            release_year=1979,
            overview="The crew of the Nostromo answers a distress call.",
            poster_path="/alien.jpg",
        )
        movie.fetched_at = datetime(2026, 9, 14, 12, 0, tzinfo=CHICAGO)
        movie.save()
        movie.genres.set(
            [
                Genre.objects.create(tmdb_id=27, name="Horror"),
                Genre.objects.create(tmdb_id=878, name="Science Fiction"),
            ]
        )
        self.saved = SavedMovie.objects.create(
            owner=self.owner,
            movie=movie,
            status=SavedMovie.Status.RENTED,
            due_at=datetime(2026, 11, 12, 12, 0, tzinfo=CHICAGO),
            rating=4,
            notes="Still terrifying.",
        )  # Private by default
        self.url = reverse("rentals:saved_detail", args=[self.saved.pk])

    def test_owner_sees_every_field_without_calling_tmdb(
        self, search_movies, get_movie_details
    ):
        self.client.force_login(self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        for expected in [
            "Alien",
            "1979",
            "https://image.tmdb.org/t/p/w342/alien.jpg",
            "The crew of the Nostromo answers a distress call.",
            "Horror",
            "Science Fiction",
            "Rented",
            "Nov 12, 2026",  # due date
            "★★★★☆",
            "Still terrifying.",
            "owner",
            "Private",
            "last updated from TMDB on Sep 14, 2026",
        ]:
            with self.subTest(expected):
                self.assertContains(response, expected)
        search_movies.assert_not_called()
        get_movie_details.assert_not_called()

    def test_viewers_excluded_by_visible_to_get_404(
        self, search_movies, get_movie_details
    ):
        other = User.objects.create_user("other", password="x")
        for label, login_as in [("other user", other), ("signed out", None)]:
            with self.subTest(label):
                self.client.logout()
                if login_as:
                    self.client.force_login(login_as)

                response = self.client.get(self.url)

                self.assertEqual(response.status_code, 404)
