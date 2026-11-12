from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rentals.models import Movie, SavedMovie

User = get_user_model()
PUBLIC = SavedMovie.Visibility.PUBLIC
SHARED = SavedMovie.Visibility.SHARED
PRIVATE = SavedMovie.Visibility.PRIVATE


class CommunityTests(TestCase):
    def setUp(self):
        self.me = User.objects.create_user("me", password="x")
        self.other = User.objects.create_user("other", password="x")
        self.url = reverse("rentals:community")
        self._next_tmdb_id = 1

    def save(self, owner, title, visibility=PRIVATE, shared_with=()):
        movie = Movie.objects.create(
            tmdb_id=self._next_tmdb_id, title=title, fetched_at=timezone.now()
        )
        self._next_tmdb_id += 1
        saved = SavedMovie.objects.create(
            owner=owner, movie=movie, visibility=visibility
        )
        saved.shared_with.set(shared_with)
        return saved

    def titles_on_page(self, response):
        return sorted(saved.movie.title for saved in response.context["saved_movies"])

    def test_signed_in_user_sees_others_public_and_shared_with_them_only(self):
        self.save(self.other, "Others Public", PUBLIC)
        self.save(self.other, "Shared With Me", SHARED, shared_with=[self.me])
        self.save(self.other, "Shared With Someone Else", SHARED, shared_with=[])
        self.save(self.other, "Others Private", PRIVATE)
        self.save(self.me, "My Public", PUBLIC)
        self.save(self.me, "My Private", PRIVATE)
        self.client.force_login(self.me)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.titles_on_page(response), ["Others Public", "Shared With Me"]
        )
        self.assertContains(response, 'data-testid="saved-card"', count=2)

    def test_signed_out_visitor_sees_public_entries_only(self):
        self.save(self.other, "Others Public", PUBLIC)
        self.save(self.me, "My Public", PUBLIC)
        self.save(self.other, "Shared With Me", SHARED, shared_with=[self.me])
        self.save(self.other, "Others Private", PRIVATE)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.titles_on_page(response), ["My Public", "Others Public"])
        self.assertNotContains(response, "Shared With Me")
        self.assertNotContains(response, "Others Private")

    def test_cards_show_owner_and_actions_only_where_viewer_can_edit(self):
        saved = self.save(self.other, "Others Public", PUBLIC)
        staff = User.objects.create_user("employee", password="x", is_staff=True)
        rent_url = reverse("rentals:saved_rent", args=[saved.pk])
        edit_url = reverse("rentals:saved_edit", args=[saved.pk])

        for label, viewer, can_edit in [
            ("other user", self.me, False),
            ("signed out", None, False),
            ("employee", staff, True),
        ]:
            with self.subTest(label):
                self.client.logout()
                if viewer:
                    self.client.force_login(viewer)

                response = self.client.get(self.url)

                self.assertContains(response, 'data-testid="card-owner"', count=1)
                self.assertContains(response, "@other")
                if can_edit:
                    self.assertContains(response, 'data-testid="card-actions"')
                    self.assertContains(response, rent_url)
                    self.assertContains(response, edit_url)
                else:
                    self.assertNotContains(response, 'data-testid="card-actions"')
                    self.assertNotContains(response, rent_url)
                    self.assertNotContains(response, edit_url)

    def test_navbar_links_to_community_and_marks_it_active(self):
        response = self.client.get(self.url)

        self.assertContains(
            response, f'<a class="nav-link active" href="{self.url}">Community</a>'
        )


class QuickActionReturnTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user("owner", password="x")
        self.staff = User.objects.create_user("employee", password="x", is_staff=True)
        movie = Movie.objects.create(
            tmdb_id=348, title="Alien", fetched_at=timezone.now()
        )
        self.saved = SavedMovie.objects.create(
            owner=owner, movie=movie, visibility=PUBLIC
        )
        self.rent_url = reverse("rentals:saved_rent", args=[self.saved.pk])
        self.client.force_login(self.staff)

    def test_staff_quick_action_on_community_returns_to_community(self):
        community = reverse("rentals:community")

        response = self.client.post(self.rent_url, {"next": community})

        self.assertRedirects(response, community)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.status, SavedMovie.Status.RENTED)

    def test_offsite_next_falls_back_to_my_library(self):
        response = self.client.post(self.rent_url, {"next": "https://evil.example/"})

        self.assertRedirects(response, reverse("rentals:library"))
