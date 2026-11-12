from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rentals.models import Movie, SavedMovie

User = get_user_model()


def edit_data(**overrides):
    data = {
        "status": "want",
        "rental_days": "2",
        "rating": "",
        "notes": "",
        "visibility": "private",
        "shared_usernames": "",
    }
    data.update(overrides)
    return data


class SharingFormTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x")
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")
        self.carol = User.objects.create_user("carol", password="x")
        movie = Movie.objects.create(
            tmdb_id=348, title="Alien", fetched_at=timezone.now()
        )
        self.saved = SavedMovie.objects.create(owner=self.owner, movie=movie)
        self.edit_url = reverse("rentals:saved_edit", args=[self.saved.pk])
        self.detail_url = self.saved.get_absolute_url()

    def test_sharing_with_usernames_lets_exactly_those_users_view(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.edit_url,
            edit_data(visibility="shared", shared_usernames="alice, bob"),
        )
        self.assertRedirects(response, self.detail_url)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.visibility, "shared")
        self.assertQuerySetEqual(
            self.saved.shared_with.order_by("username"),
            [self.alice, self.bob],
        )

        for user, can_view in [
            (self.alice, True),
            (self.bob, True),
            (self.carol, False),
        ]:
            with self.subTest(user.username):
                self.client.force_login(user)
                expected = 200 if can_view else 404
                self.assertEqual(self.client.get(self.detail_url).status_code, expected)

    def test_unknown_username_is_a_form_error_and_nothing_changes(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.edit_url,
            edit_data(visibility="shared", shared_usernames="alice, nobody"),
        )
        self.assertEqual(response.status_code, 200)
        errors = response.context["form"].errors.get("shared_usernames", [])
        self.assertTrue(any("nobody" in error for error in errors), errors)
        self.assertContains(response, "nobody")
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.visibility, "private")
        self.assertFalse(self.saved.shared_with.exists())

    def test_shared_needs_at_least_one_username(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.edit_url, edit_data(visibility="shared", shared_usernames=" , ")
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors.get("shared_usernames"))
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.visibility, "private")


class WebsitePermissionMatrixTests(TestCase):
    """Owner, other user, shared-with user, employee, admin, signed-out
    × Private/Public/Shared × view/edit, all through the website."""

    VIEW = {
        # viewer: visibilities they may view
        "owner": {"private", "public", "shared"},
        "other": {"public"},
        "friend": {"public", "shared"},
        "employee": {"private", "public", "shared"},
        "admin": {"private", "public", "shared"},
        "signed_out": {"public"},
    }
    EDIT = {"owner", "employee", "admin"}

    def setUp(self):
        owner = User.objects.create_user("owner", password="x")
        friend = User.objects.create_user("friend", password="x")
        self.viewers = {
            "owner": owner,
            "other": User.objects.create_user("other", password="x"),
            "friend": friend,
            "employee": User.objects.create_user(
                "employee", password="x", is_staff=True
            ),
            "admin": User.objects.create_superuser("admin", password="x"),
            "signed_out": None,
        }
        self.entries = {}
        for tmdb_id, visibility in enumerate(("private", "public", "shared"), 1):
            saved = SavedMovie.objects.create(
                owner=owner,
                movie=Movie.objects.create(
                    tmdb_id=tmdb_id, title=f"Film {tmdb_id}", fetched_at=timezone.now()
                ),
                visibility=visibility,
                notes=f"secret notes {visibility}",
            )
            # The friend is listed on every entry, to prove the list only
            # matters when the visibility is Shared.
            saved.shared_with.add(friend)
            self.entries[visibility] = saved

    def login(self, name):
        self.client.logout()
        if self.viewers[name]:
            self.client.force_login(self.viewers[name])

    def test_view(self):
        for name in self.viewers:
            for visibility, saved in self.entries.items():
                with self.subTest(viewer=name, visibility=visibility):
                    self.login(name)
                    response = self.client.get(saved.get_absolute_url())
                    if visibility in self.VIEW[name]:
                        # Notes follow the entry's visibility.
                        self.assertContains(response, saved.notes)
                    else:
                        self.assertEqual(response.status_code, 404)

    def test_edit(self):
        for name in self.viewers:
            for visibility, saved in self.entries.items():
                with self.subTest(viewer=name, visibility=visibility):
                    self.login(name)
                    edit_url = reverse("rentals:saved_edit", args=[saved.pk])
                    get = self.client.get(edit_url)
                    post = self.client.post(
                        edit_url,
                        edit_data(
                            visibility=visibility,
                            shared_usernames="friend",
                            notes=f"edited by {name}",
                        ),
                    )
                    saved.refresh_from_db()
                    if name in self.EDIT:
                        self.assertEqual(get.status_code, 200)
                        self.assertRedirects(post, saved.get_absolute_url())
                        self.assertEqual(saved.notes, f"edited by {name}")
                    else:
                        if name == "signed_out":
                            login = reverse("accounts:login")
                            self.assertRedirects(get, f"{login}?next={edit_url}")
                            self.assertRedirects(post, f"{login}?next={edit_url}")
                        else:
                            self.assertEqual(get.status_code, 404)
                            self.assertEqual(post.status_code, 404)
                        self.assertNotEqual(saved.notes, f"edited by {name}")
                    self.assertEqual(saved.visibility, visibility)

    def test_delete(self):
        for name in ("other", "friend", "signed_out", "employee"):
            saved = self.entries["shared"]
            with self.subTest(viewer=name):
                self.login(name)
                self.client.post(reverse("rentals:saved_delete", args=[saved.pk]))
                exists = SavedMovie.objects.filter(pk=saved.pk).exists()
                self.assertEqual(exists, name not in self.EDIT)


class PrivacyDisplayTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x")
        self.friend = User.objects.create_user("friend", password="x")
        self.saved = SavedMovie.objects.create(
            owner=self.owner,
            movie=Movie.objects.create(
                tmdb_id=348, title="Alien", fetched_at=timezone.now()
            ),
            visibility=SavedMovie.Visibility.SHARED,
        )
        self.saved.shared_with.add(self.friend)

    def test_edit_page_explains_private_default_and_staff_access(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("rentals:saved_edit", args=[self.saved.pk]))
        self.assertContains(response, 'data-testid="privacy-note"')
        self.assertContains(response, "starts out <strong>Private</strong>")
        self.assertContains(response, "employees and admins can still see all")
        # The current share list is pre-filled.
        self.assertContains(response, 'value="friend"')

    def test_new_entries_default_to_private(self):
        other = SavedMovie.objects.create(
            owner=self.owner,
            movie=Movie.objects.create(tmdb_id=1, title="X", fetched_at=timezone.now()),
        )
        self.assertEqual(other.visibility, SavedMovie.Visibility.PRIVATE)

    def test_card_and_detail_show_visibility_icon(self):
        self.client.force_login(self.owner)
        library = self.client.get(reverse("rentals:library"))
        self.assertContains(library, 'data-visibility="shared"')
        detail = self.client.get(self.saved.get_absolute_url())
        self.assertContains(detail, 'data-visibility="shared"')

    def test_share_list_shown_to_owner_but_not_to_shared_users(self):
        self.client.force_login(self.owner)
        self.assertContains(
            self.client.get(self.saved.get_absolute_url()), 'data-testid="shared-with"'
        )
        self.client.force_login(self.friend)
        self.assertNotContains(
            self.client.get(self.saved.get_absolute_url()), 'data-testid="shared-with"'
        )

    def test_switching_away_from_shared_needs_no_usernames(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("rentals:saved_edit", args=[self.saved.pk]),
            edit_data(visibility="public", shared_usernames=""),
        )
        self.assertRedirects(response, self.saved.get_absolute_url())
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.visibility, "public")
