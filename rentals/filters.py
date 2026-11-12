"""The one filter set behind My Library, Community and (later) the API.

Every filter runs on local data only, over a starting queryset that the
caller has already limited to rows the viewer may see (``visible_to``), so
search can never match another user's Private notes.
"""

from datetime import datetime, time

import django_filters
from django import forms
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone

from .models import Genre, SavedMovie

MIN_RATING_CHOICES = [(n, f"{n}★ and up") for n in range(1, 6)]

SORT_CHOICES = [
    ("saved_new", "Date saved (newest)"),
    ("saved_old", "Date saved (oldest)"),
    ("title", "Title A–Z"),
    ("year_new", "Release year (newest)"),
    ("year_old", "Release year (oldest)"),
    ("rating_high", "My rating (highest)"),
    ("rating_low", "My rating (lowest)"),
]
# Each sort's ordering, before the shared tie-breaker. Unrated entries
# (NULL rating) and movies with no release year go last in either direction.
# Title sort is plain A–Z (no "The/A/An" handling).
SORT_ORDERINGS = {
    "saved_new": [],  # the tie-breaker alone is "newest saved first"
    "saved_old": ["created_at", "id"],
    "title": [Lower("movie__title")],
    "year_new": [F("movie__release_year").desc(nulls_last=True)],
    "year_old": [F("movie__release_year").asc(nulls_last=True)],
    "rating_high": [F("rating").desc(nulls_last=True)],
    "rating_low": [F("rating").asc(nulls_last=True)],
}


class SavedMovieFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search", label="Search")
    status = django_filters.ChoiceFilter(
        choices=SavedMovie.Status.choices, empty_label="Any status"
    )
    genre = django_filters.ModelChoiceFilter(
        field_name="movie__genres",
        queryset=Genre.objects.all(),
        empty_label="Any genre",
    )
    # rating >= N also leaves out unrated entries (NULL never matches).
    min_rating = django_filters.ChoiceFilter(
        field_name="rating",
        lookup_expr="gte",
        choices=MIN_RATING_CHOICES,
        empty_label="Any rating",
        label="Minimum rating",
    )
    visibility = django_filters.ChoiceFilter(
        choices=SavedMovie.Visibility.choices, empty_label="Any visibility"
    )
    overdue = django_filters.BooleanFilter(
        method="filter_overdue",
        widget=forms.CheckboxInput,
        label="Overdue only",
    )
    sort = django_filters.ChoiceFilter(
        method="filter_sort",
        choices=SORT_CHOICES,
        empty_label=None,
        label="Sort by",
    )

    class Meta:
        model = SavedMovie
        fields = []

    def filter_search(self, queryset, name, value):
        """Case-insensitive match on the movie title or the notes.

        Only narrows ``queryset``, which already holds just the rows the
        viewer may see, so other users' Private notes can never match.
        """
        return queryset.filter(
            Q(movie__title__icontains=value) | Q(notes__icontains=value)
        )

    def filter_overdue(self, queryset, name, value):
        """Rented and due before the start of today (same rule as ``is_overdue``).

        A rental due today is not overdue. An unticked box means no filter.
        """
        if not value:
            return queryset
        start_of_today = timezone.make_aware(
            datetime.combine(timezone.localdate(), time.min)
        )
        return queryset.filter(
            status=SavedMovie.Status.RENTED, due_at__lt=start_of_today
        )

    def filter_sort(self, queryset, name, value):
        ordering = SORT_ORDERINGS.get(value)
        if ordering is None:
            return queryset
        # Newest saved first breaks every tie, so pages stay consistent.
        return queryset.order_by(*ordering, "-created_at", "-id")


class CommunitySavedMovieFilter(SavedMovieFilter):
    """Community offers every filter except visibility."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.filters["visibility"]
