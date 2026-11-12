"""Search, filters, sorting and pagination on My Library and Community."""

from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rentals.models import Genre, Movie, SavedMovie

User = get_user_model()


class BrowseTestCase(TestCase):
    def setUp(self):
        self.me = User.objects.create_user("me", password="x")
        self.other = User.objects.create_user("other", password="x")
        self.library_url = reverse("rentals:library")
        self.community_url = reverse("rentals:community")
        self._next_tmdb_id = 1

    def save(self, owner, title, **fields):
        movie_fields = {
            key: fields.pop(key) for key in ["release_year"] if key in fields
        }
        movie = Movie.objects.create(
            tmdb_id=self._next_tmdb_id,
            title=title,
            fetched_at=timezone.now(),
            **movie_fields,
        )
        self._next_tmdb_id += 1
        return SavedMovie.objects.create(owner=owner, movie=movie, **fields)

    def titles(self, response):
        """Titles on the page, in the order shown."""
        return [saved.movie.title for saved in response.context["saved_movies"]]


class SearchPrivacyTests(BrowseTestCase):
    def test_community_search_never_matches_other_users_private_notes(self):
        public = SavedMovie.Visibility.PUBLIC
        self.save(self.other, "Heat", visibility=public, notes="A secret twist")
        self.save(self.other, "Rashomon", notes="A secret twist")  # Private
        self.save(self.other, "Alien", visibility=public, notes="Scary")
        self.client.force_login(self.me)

        response = self.client.get(self.community_url, {"q": "Secret"})

        self.assertEqual(self.titles(response), ["Heat"])
        self.assertNotContains(response, "Rashomon")


class OverdueFilterTests(BrowseTestCase):
    def test_overdue_only_keeps_rentals_due_before_today(self):
        rented = SavedMovie.Status.RENTED
        now = timezone.now()
        start_of_today = timezone.make_aware(
            datetime.combine(timezone.localdate(), time.min)
        )
        self.save(self.me, "Late", status=rented, due_at=now - timedelta(days=1))
        self.save(
            self.me,
            "Due Today",
            status=rented,
            due_at=start_of_today + timedelta(minutes=1),
        )
        self.save(
            self.me, "Due Tomorrow", status=rented, due_at=now + timedelta(days=1)
        )
        # Not Rented, so never overdue even with a past due date.
        self.save(
            self.me,
            "Returned",
            status=SavedMovie.Status.WATCHED,
            due_at=now - timedelta(days=3),
        )
        self.client.force_login(self.me)

        response = self.client.get(self.library_url, {"overdue": "on"})

        self.assertEqual(self.titles(response), ["Late"])


class SortTests(BrowseTestCase):
    def test_rating_sort_puts_unrated_last_in_both_directions_with_stable_ties(self):
        # Saved in this order, so "newest saved first" is the reverse of it.
        self.save(self.me, "Alpha", rating=3)
        self.save(self.me, "Beta")
        self.save(self.me, "Gamma", rating=5)
        self.save(self.me, "Delta")
        self.save(self.me, "Epsilon", rating=3)
        self.client.force_login(self.me)

        # Equal ratings (and the unrated group) fall back to newest saved first.
        cases = [
            ("rating_high", ["Gamma", "Epsilon", "Alpha", "Delta", "Beta"]),
            ("rating_low", ["Epsilon", "Alpha", "Gamma", "Delta", "Beta"]),
        ]
        for sort, expected in cases:
            with self.subTest(sort):
                response = self.client.get(self.library_url, {"sort": sort})

                self.assertEqual(self.titles(response), expected)

    def test_other_sorts(self):
        self.save(self.me, "beta", release_year=1999)
        self.save(self.me, "Alpha", release_year=2010)
        self.save(self.me, "Gamma")  # no release year
        self.save(self.me, "Delta", release_year=1999)
        self.client.force_login(self.me)

        cases = [
            (None, ["Delta", "Gamma", "Alpha", "beta"]),
            ("saved_new", ["Delta", "Gamma", "Alpha", "beta"]),
            ("saved_old", ["beta", "Alpha", "Gamma", "Delta"]),
            ("title", ["Alpha", "beta", "Delta", "Gamma"]),
            # Equal years fall back to newest saved; no year goes last.
            ("year_new", ["Alpha", "Delta", "beta", "Gamma"]),
            ("year_old", ["Delta", "beta", "Alpha", "Gamma"]),
            ("nonsense", ["Delta", "Gamma", "Alpha", "beta"]),
        ]
        for sort, expected in cases:
            with self.subTest(sort):
                params = {"sort": sort} if sort else {}
                response = self.client.get(self.library_url, params)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.titles(response), expected)


class FilterTests(BrowseTestCase):
    def setUp(self):
        super().setUp()
        drama = Genre.objects.create(tmdb_id=18, name="Drama")
        horror = Genre.objects.create(tmdb_id=27, name="Horror")
        self.drama = drama
        public = SavedMovie.Visibility.PUBLIC
        rented = SavedMovie.Status.RENTED
        for owner in [self.me, self.other]:
            heat = self.save(owner, "Heat", rating=5, visibility=public)
            heat.movie.genres.add(drama)
            alien = self.save(owner, "Alien", rating=3, status=rented)
            alien.movie.genres.add(horror)
            self.save(owner, "Up", visibility=public, notes="Balloons")

    def test_each_filter_narrows_my_library(self):
        self.client.force_login(self.me)
        cases = [
            ({"q": "alien"}, ["Alien"]),
            ({"q": "BALLOON"}, ["Up"]),
            ({"status": "rented"}, ["Alien"]),
            ({"genre": self.drama.pk}, ["Heat"]),
            ({"min_rating": 3}, ["Alien", "Heat"]),
            ({"min_rating": 4}, ["Heat"]),
            ({"visibility": "public"}, ["Heat", "Up"]),
            ({"visibility": "private"}, ["Alien"]),
            ({"status": "want", "visibility": "public"}, ["Heat", "Up"]),
            ({"status": "want", "min_rating": 1}, ["Heat"]),
        ]
        for params, expected in cases:
            with self.subTest(params):
                response = self.client.get(self.library_url, params)

                self.assertEqual(sorted(self.titles(response)), expected)

    def test_community_filters_work_but_visibility_is_not_offered(self):
        staff = User.objects.create_user("employee", password="x", is_staff=True)
        self.client.force_login(staff)  # staff see both users' entries

        response = self.client.get(
            self.community_url, {"min_rating": 4, "genre": self.drama.pk}
        )
        self.assertEqual(self.titles(response), ["Heat", "Heat"])

        response = self.client.get(self.community_url, {"visibility": "public"})
        self.assertNotIn("visibility", response.context["filter_form"].fields)
        self.assertNotContains(response, 'name="visibility"')
        self.assertEqual(len(self.titles(response)), 6)  # ignored, not applied

        response = self.client.get(self.library_url)
        self.assertContains(response, 'name="visibility"')

    def test_no_match_shows_message_and_clear_filters_link(self):
        self.client.force_login(self.me)

        response = self.client.get(self.library_url, {"q": "zzz"})

        self.assertContains(response, 'data-testid="filters-empty"')
        self.assertContains(response, "No saved movies match these filters")
        self.assertContains(
            response,
            f'<a href="{self.library_url}" class="btn btn-sm btn-outline-secondary">Clear filters</a>',
        )
        self.assertNotContains(response, 'data-testid="library-empty"')


class PaginationTests(BrowseTestCase):
    def setUp(self):
        super().setUp()
        for n in range(1, 26):  # 25 entries: pages of 12, 12 and 1
            self.save(self.me, f"Movie {n:02}", notes="even" if n % 2 == 0 else "")
        self.client.force_login(self.me)

    def test_pages_hold_twelve_results(self):
        response = self.client.get(self.library_url)

        self.assertEqual(len(self.titles(response)), 12)
        self.assertEqual(self.titles(response)[0], "Movie 25")
        self.assertContains(response, "Page 1 of 3")
        self.assertContains(response, "25 saved movies")

        response = self.client.get(self.library_url, {"page": 3})
        self.assertEqual(self.titles(response), ["Movie 01"])

    def test_out_of_range_or_bad_page_numbers(self):
        cases = [("99", 3), ("0", 3), ("abc", 1), ("", 1)]
        for page, expected in cases:
            with self.subTest(page):
                response = self.client.get(self.library_url, {"page": page})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["page_obj"].number, expected)

    def test_page_links_keep_filters_and_filter_form_starts_at_page_one(self):
        response = self.client.get(
            self.library_url, {"q": "even", "sort": "title", "page": 1}
        )

        self.assertEqual(response.context["page_obj"].paginator.count, 12)
        self.assertNotContains(response, 'data-testid="pagination"')

        response = self.client.get(self.library_url, {"sort": "title", "page": 2})
        self.assertContains(response, 'href="?sort=title&amp;page=1"')
        self.assertContains(response, 'href="?sort=title&amp;page=3"')
        # The filter form has no page field, so submitting it resets to page 1.
        self.assertNotContains(response, 'name="page"')
