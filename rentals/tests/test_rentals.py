from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from rentals.models import Movie, SavedMovie

User = get_user_model()
CHICAGO = ZoneInfo("America/Chicago")


def make_saved(username="owner", tmdb_id=348, title="Alien", **fields):
    owner = User.objects.create_user(username, password="x")
    movie = Movie.objects.create(
        tmdb_id=tmdb_id, title=title, fetched_at=timezone.now()
    )
    return SavedMovie.objects.create(owner=owner, movie=movie, **fields)


class RentalRuleTests(TestCase):
    def test_rent_return_and_re_rent(self):
        saved = make_saved()
        first_rent = datetime(2026, 11, 1, 10, 0, tzinfo=CHICAGO)
        returned = datetime(2026, 11, 3, 9, 0, tzinfo=CHICAGO)
        re_rent = datetime(2026, 11, 8, 20, 0, tzinfo=CHICAGO)

        with self.subTest("renting sets rented_at and due_at from the length"):
            with patch("django.utils.timezone.now", return_value=first_rent):
                saved.change_status(SavedMovie.Status.RENTED, rental_days=7)
            self.assertEqual(saved.status, SavedMovie.Status.RENTED)
            self.assertEqual(saved.rented_at, first_rent)
            self.assertEqual(saved.due_at, first_rent + timedelta(days=7))

        with self.subTest("leaving Rented clears due_at and keeps rented_at"):
            with patch("django.utils.timezone.now", return_value=returned):
                saved.change_status(SavedMovie.Status.WATCHED)
            self.assertEqual(saved.status, SavedMovie.Status.WATCHED)
            self.assertIsNone(saved.due_at)
            self.assertEqual(saved.rented_at, first_rent)

        with self.subTest(
            "re-renting from Watched starts a new period (default 2 days)"
        ):
            with patch("django.utils.timezone.now", return_value=re_rent):
                saved.change_status(SavedMovie.Status.RENTED)
            self.assertEqual(saved.rented_at, re_rent)
            self.assertEqual(saved.due_at, re_rent + timedelta(days=2))


class OverdueTests(TestCase):
    def test_overdue_only_when_due_before_today(self):
        # "Now" is 8:00 am on Nov 10 in the site's time zone (America/Chicago).
        now = datetime(2026, 11, 10, 8, 0, tzinfo=CHICAGO)
        rented = SavedMovie.Status.RENTED
        cases = [
            (
                "due yesterday evening",
                rented,
                datetime(2026, 11, 9, 23, 0, tzinfo=CHICAGO),
                True,
            ),
            (
                "due earlier today",
                rented,
                datetime(2026, 11, 10, 0, 30, tzinfo=CHICAGO),
                False,
            ),
            (
                "due later today",
                rented,
                datetime(2026, 11, 10, 22, 0, tzinfo=CHICAGO),
                False,
            ),
            (
                "due tomorrow",
                rented,
                datetime(2026, 11, 11, 9, 0, tzinfo=CHICAGO),
                False,
            ),
            (
                "watched, old due date",
                SavedMovie.Status.WATCHED,
                datetime(2026, 11, 1, tzinfo=CHICAGO),
                False,
            ),
            ("rented, no due date", rented, None, False),
        ]
        saved = make_saved()
        for label, status, due_at, expected in cases:
            with self.subTest(label):
                saved.status, saved.due_at = status, due_at
                with patch("django.utils.timezone.now", return_value=now):
                    self.assertEqual(saved.is_overdue, expected)
