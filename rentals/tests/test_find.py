from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rentals import tmdb

User = get_user_model()

ALIEN = {
    "id": 348,
    "title": "Alien",
    "release_date": "1979-05-25",
    "overview": "During its return to the earth, commercial spaceship Nostromo...",
    "poster_path": "/vfrQk5IPloGg1v9Rzbh2Eg3VGyM.jpg",
}
ALIENS = {
    "id": 679,
    "title": "Aliens",
    "release_date": "1986-07-18",
    "overview": "Ripley wakes up after 57 years in hyper-sleep.",
    "poster_path": "/r1x5JGpyqZU8PYhbs4UcrO1Xb6x.jpg",
}


class FindPageResultsTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("moviefan", password="x"))

    @patch("rentals.tmdb.search_movies")
    def test_results_show_as_poster_cards_with_prev_and_next(self, search_movies):
        search_movies.return_value = {
            "results": [ALIEN, ALIENS],
            "page": 2,
            "total_pages": 5,
        }
        find = reverse("rentals:find")

        response = self.client.get(find, {"q": "alien", "page": "2"})

        search_movies.assert_called_once_with("alien", page=2)
        for movie, year in [(ALIEN, "1979"), (ALIENS, "1986")]:
            self.assertContains(response, movie["title"])
            self.assertContains(response, year)
            self.assertContains(response, movie["overview"])
            self.assertContains(
                response, f"https://image.tmdb.org/t/p/w342{movie['poster_path']}"
            )
        self.assertContains(response, f'href="{find}?q=alien&amp;page=1"')
        self.assertContains(response, f'href="{find}?q=alien&amp;page=3"')


UNREACHABLE_MESSAGE = (
    "Couldn't reach TMDB right now. Your saved movies still work. "
    "Try again in a minute."
)
GENERIC_MESSAGE = "Movie search is temporarily unavailable."


class FindPageTMDBUnavailableTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("moviefan", password="x"))
        # Report server errors as responses (as a browser sees them), not exceptions.
        self.client.raise_request_exception = False

    def test_failure_shows_friendly_message_without_technical_detail(self):
        cases = [
            ("unreachable", True, UNREACHABLE_MESSAGE, GENERIC_MESSAGE),
            ("bad token / rate limit / 5xx", False, GENERIC_MESSAGE, "Couldn't reach"),
        ]
        for name, unreachable, shown, not_shown in cases:
            with self.subTest(name), patch("rentals.tmdb.search_movies") as search:
                search.side_effect = tmdb.TMDBUnavailable(
                    "TECHNICAL-DETAIL status 401", unreachable=unreachable
                )

                response = self.client.get(reverse("rentals:find"), {"q": "alien"})

                self.assertContains(response, shown)
                self.assertContains(response, 'class="alert alert-')
                self.assertNotContains(response, not_shown)
                self.assertNotContains(response, "TECHNICAL-DETAIL")


class FindPageTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("moviefan", password="x"))

    def test_find_page_requires_login(self):
        self.client.logout()
        url = reverse("rentals:find")

        with patch("rentals.tmdb.search_movies") as search:
            response = self.client.get(url, {"q": "alien"})

        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={url}%3Fq%3Dalien"
        )
        search.assert_not_called()

    def test_navbar_search_box_submits_to_find_page(self):
        response = self.client.get(reverse("rentals:home"))

        self.assertContains(response, f'action="{reverse("rentals:find")}"')
        self.assertContains(response, 'name="q"')

    def test_empty_query_does_not_call_tmdb(self):
        with patch("rentals.tmdb.search_movies") as search:
            response = self.client.get(reverse("rentals:find"), {"q": "   "})

        search.assert_not_called()
        self.assertContains(response, "Type a movie title in the search box")

    @patch("rentals.tmdb.search_movies")
    def test_zero_results_says_no_movies_found(self, search_movies):
        search_movies.return_value = {"results": [], "page": 1, "total_pages": 0}

        response = self.client.get(reverse("rentals:find"), {"q": "zzzz"})

        self.assertContains(response, "No movies found for “zzzz”.")

    @patch("rentals.tmdb.search_movies")
    def test_first_page_has_no_prev_link_and_query_stays_in_search_box(
        self, search_movies
    ):
        search_movies.return_value = {"results": [ALIEN], "page": 1, "total_pages": 3}
        find = reverse("rentals:find")

        response = self.client.get(find, {"q": "alien"})

        search_movies.assert_called_once_with("alien", page=1)
        self.assertNotContains(response, f'href="{find}?q=alien&amp;page=0"')
        self.assertContains(response, f'href="{find}?q=alien&amp;page=2"')
        self.assertContains(response, 'value="alien"')

    @patch("rentals.tmdb.search_movies")
    def test_bad_page_number_falls_back_to_page_one(self, search_movies):
        search_movies.return_value = {"results": [], "page": 1, "total_pages": 0}

        self.client.get(reverse("rentals:find"), {"q": "alien", "page": "abc"})

        search_movies.assert_called_once_with("alien", page=1)

    @patch("rentals.tmdb.search_movies")
    def test_movie_without_poster_or_date_shows_placeholders(self, search_movies):
        bare = {"id": 1, "title": "Lost Film", "release_date": "", "poster_path": None}
        search_movies.return_value = {"results": [bare], "page": 1, "total_pages": 1}

        response = self.client.get(reverse("rentals:find"), {"q": "lost"})

        self.assertContains(response, "No poster")
        self.assertContains(response, "Year unknown")
        self.assertNotContains(response, "image.tmdb.org/t/p/w342None")
