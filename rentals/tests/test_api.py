"""The saved-entries API: scopes, the view rule, filters, auth and embedding."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from rentals.models import Movie, SavedMovie
from rentals.serializers import MovieSerializer, SavedMovieSerializer

User = get_user_model()

PRIVATE = SavedMovie.Visibility.PRIVATE
PUBLIC = SavedMovie.Visibility.PUBLIC
SHARED = SavedMovie.Visibility.SHARED


class APITestBase(APITestCase):
    list_url = reverse("api:saved-list")

    def setUp(self):
        self.me = User.objects.create_user("me", password="x")
        self.other = User.objects.create_user("other", password="x")
        self._next_tmdb_id = 1

    def save(self, owner, title, *, shared_with=(), **fields):
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
        saved = SavedMovie.objects.create(owner=owner, movie=movie, **fields)
        saved.shared_with.set(shared_with)
        return saved

    def api_titles(self, response):
        return [entry["movie"]["title"] for entry in response.data["results"]]

    def website_titles(self, url, params=None):
        response = self.client.get(url, params or {})
        return [saved.movie.title for saved in response.context["saved_movies"]]


class CommunityScopeTests(APITestBase):
    def test_community_scope_matches_the_website_community_page(self):
        self.save(self.me, "My Own Public", visibility=PUBLIC)
        self.save(self.other, "Their Public", visibility=PUBLIC)
        self.save(
            self.other, "Shared With Me", visibility=SHARED, shared_with=[self.me]
        )
        self.save(self.other, "Shared Elsewhere", visibility=SHARED)
        self.save(self.other, "Their Private", visibility=PRIVATE)
        self.client.force_login(self.me)

        response = self.client.get(self.list_url, {"scope": "community"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.api_titles(response), ["Shared With Me", "Their Public"])
        self.assertEqual(
            self.api_titles(response),
            self.website_titles(reverse("rentals:community")),
        )


class RetrievePermissionTests(APITestBase):
    """The view side of the matrix: who may retrieve each kind of entry."""

    def test_retrieve_follows_the_view_rule(self):
        friend = User.objects.create_user("friend", password="x")
        employee = User.objects.create_user("employee", password="x", is_staff=True)
        admin = User.objects.create_superuser("admin", password="x")
        entries = {
            PRIVATE: self.save(self.me, "Private One", visibility=PRIVATE),
            PUBLIC: self.save(self.me, "Public One", visibility=PUBLIC),
            SHARED: self.save(
                self.me, "Shared One", visibility=SHARED, shared_with=[friend]
            ),
        }
        # viewer -> visibilities that viewer may see
        expected = {
            "owner": {PRIVATE, PUBLIC, SHARED},
            "other user": {PUBLIC},
            "shared-with user": {PUBLIC, SHARED},
            "employee": {PRIVATE, PUBLIC, SHARED},
            "admin": {PRIVATE, PUBLIC, SHARED},
            "signed out": {PUBLIC},
        }
        viewers = {
            "owner": self.me,
            "other user": self.other,
            "shared-with user": friend,
            "employee": employee,
            "admin": admin,
            "signed out": None,
        }
        for viewer_name, viewer in viewers.items():
            for visibility, saved in entries.items():
                with self.subTest(viewer=viewer_name, visibility=visibility):
                    self.client.logout()
                    if viewer:
                        self.client.force_login(viewer)
                    url = reverse("api:saved-detail", args=[saved.pk])

                    response = self.client.get(url)

                    if visibility in expected[viewer_name]:
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.data["id"], saved.pk)
                    else:
                        self.assertEqual(response.status_code, 404)


class FilterSortPageTests(APITestBase):
    def test_search_filter_sort_and_pages_match_the_website(self):
        # 14 of my entries: ratings cycle 1..5 then unrated, so some are unrated.
        for n in range(14):
            rating = (n % 6) + 1 if n % 6 != 5 else None
            notes = "cozy" if n % 2 else ""
            self.save(self.me, f"Movie {n:02}", rating=rating, notes=notes)
        self.client.force_login(self.me)
        library_url = reverse("rentals:library")

        cases = [
            {},
            {"page": "2"},
            {"sort": "rating_low"},
            {"sort": "rating_low", "page": "2"},  # unrated land on page 2
            {"sort": "title", "q": "cozy"},
            {"min_rating": "3", "sort": "rating_high"},
            {"page": "99"},  # past the end: the last page, like the website
        ]
        for params in cases:
            with self.subTest(**params):
                response = self.client.get(self.list_url, params)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data["count"],
                    self.client.get(library_url, params)
                    .context["page_obj"]
                    .paginator.count,
                )
                self.assertEqual(
                    self.api_titles(response),
                    self.website_titles(library_url, params),
                )


class ScopeTests(APITestBase):
    def test_mine_is_the_default_and_lists_only_my_entries(self):
        self.save(self.me, "Mine Private")
        self.save(self.me, "Mine Public", visibility=PUBLIC)
        self.save(self.other, "Theirs Public", visibility=PUBLIC)
        self.client.force_login(self.me)

        for params in [{}, {"scope": "mine"}]:
            with self.subTest(**params):
                response = self.client.get(self.list_url, params)
                self.assertEqual(
                    self.api_titles(response), ["Mine Public", "Mine Private"]
                )

    def test_signed_out_mine_is_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 401)

    def test_unknown_scope_is_400(self):
        self.client.force_login(self.me)
        response = self.client.get(self.list_url, {"scope": "everyone"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("scope", response.data)

    def test_community_ignores_the_visibility_filter_like_the_website(self):
        self.save(self.other, "Their Public", visibility=PUBLIC)
        self.save(self.other, "Shared", visibility=SHARED, shared_with=[self.me])
        self.client.force_login(self.me)
        params = {"scope": "community", "visibility": "public"}

        response = self.client.get(self.list_url, params)

        self.assertEqual(self.api_titles(response), ["Shared", "Their Public"])


class SignedOutTests(APITestBase):
    def test_signed_out_community_lists_public_entries_only(self):
        self.save(self.me, "Public", visibility=PUBLIC)
        self.save(self.other, "Private")
        self.save(self.other, "Shared", visibility=SHARED, shared_with=[self.me])

        response = self.client.get(self.list_url, {"scope": "community"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.api_titles(response), ["Public"])

    def test_signed_out_writes_are_refused_with_401(self):
        saved = self.save(self.me, "Public", visibility=PUBLIC)
        detail_url = reverse("api:saved-detail", args=[saved.pk])
        self.assertEqual(self.client.post(self.list_url, {}).status_code, 401)
        self.assertEqual(self.client.delete(detail_url).status_code, 401)
        self.assertTrue(SavedMovie.objects.filter(pk=saved.pk).exists())


class TokenAuthTests(APITestBase):
    token_url = reverse("api:token")

    def test_token_endpoint_returns_a_token_that_authenticates(self):
        self.save(self.me, "Mine")
        response = self.client.post(self.token_url, {"username": "me", "password": "x"})
        self.assertEqual(response.status_code, 200)
        token = response.data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.api_titles(response), ["Mine"])

    def test_wrong_password_gets_no_token(self):
        response = self.client.post(
            self.token_url, {"username": "me", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("token", response.data)

    def test_bad_token_is_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")
        self.assertEqual(self.client.get(self.list_url).status_code, 401)


class BrowsableAPITests(APITestBase):
    def test_browsable_api_works_with_a_session_login(self):
        self.save(self.me, "Mine")
        self.assertTrue(self.client.login(username="me", password="x"))

        response = self.client.get(self.list_url, HTTP_ACCEPT="text/html")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django REST framework")
        self.assertContains(response, "Mine")


class EmbeddedMovieTests(APITestBase):
    def test_entry_embeds_the_movie_details(self):
        saved = self.save(self.me, "Alien", release_year=1979, rating=4)
        movie = saved.movie
        movie.overview = "In space no one can hear you scream."
        movie.poster_path = "/alien.jpg"
        movie.save()
        movie.genres.create(tmdb_id=27, name="Horror")
        self.client.force_login(self.me)

        data = self.client.get(reverse("api:saved-detail", args=[saved.pk])).data

        self.assertEqual(data["owner"], "me")
        self.assertEqual(data["rating"], 4)
        self.assertEqual(data["visibility"], PRIVATE)
        self.assertFalse(data["is_overdue"])
        embedded = data["movie"]
        self.assertEqual(embedded["tmdb_id"], movie.tmdb_id)
        self.assertEqual(embedded["title"], "Alien")
        self.assertEqual(embedded["release_year"], 1979)
        self.assertEqual(embedded["overview"], "In space no one can hear you scream.")
        self.assertEqual(embedded["poster_path"], "/alien.jpg")
        self.assertEqual(
            embedded["poster_url"], "https://image.tmdb.org/t/p/w342/alien.jpg"
        )
        self.assertEqual(embedded["genres"], [{"tmdb_id": 27, "name": "Horror"}])
        self.assertIsNotNone(embedded["fetched_at"])

    def test_movie_details_are_read_only(self):
        self.assertTrue(SavedMovieSerializer().fields["movie"].read_only)
        for name, field in MovieSerializer().fields.items():
            with self.subTest(field=name):
                self.assertTrue(field.read_only)


class SharedWithTests(APITestBase):
    def test_only_owner_and_staff_see_who_an_entry_is_shared_with(self):
        friend = User.objects.create_user("friend", password="x")
        employee = User.objects.create_user("employee", password="x", is_staff=True)
        saved = self.save(self.me, "Shared", visibility=SHARED, shared_with=[friend])
        url = reverse("api:saved-detail", args=[saved.pk])

        for viewer, sees_list in [(self.me, True), (employee, True), (friend, False)]:
            with self.subTest(viewer=viewer.username):
                self.client.force_login(viewer)
                data = self.client.get(url).data
                if sees_list:
                    self.assertEqual(data["shared_with"], ["friend"])
                else:
                    self.assertNotIn("shared_with", data)
