from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .permissions import is_staff_user

RENTAL_DAY_CHOICES = [(1, "1 day"), (2, "2 days"), (7, "7 days")]
DEFAULT_RENTAL_DAYS = 2


class Genre(models.Model):
    """A TMDB genre. ``tmdb_id`` is TMDB's own genre ID."""

    tmdb_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Movie(models.Model):
    """One shared row per TMDB film. Only the server creates or updates it."""

    tmdb_id = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=255)
    release_year = models.PositiveSmallIntegerField(null=True, blank=True)
    overview = models.TextField(blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    genres = models.ManyToManyField(Genre, blank=True, related_name="movies")
    fetched_at = models.DateTimeField()

    class Meta:
        ordering = ["title"]

    def __str__(self):
        if self.release_year:
            return f"{self.title} ({self.release_year})"
        return self.title

    @property
    def poster_url(self):
        if not self.poster_path:
            return ""
        return f"https://image.tmdb.org/t/p/w342{self.poster_path}"


class SavedMovieQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Entries ``user`` may view: the single view rule used everywhere.

        The owner and staff see everything; anyone sees Public entries; a
        Shared entry is also visible to the users listed in ``shared_with``.
        Signed-out viewers see Public entries only.
        """
        if is_staff_user(user):
            return self.all()
        public = models.Q(visibility=SavedMovie.Visibility.PUBLIC)
        if not user or not user.is_authenticated:
            return self.filter(public)
        shared_with_user = models.Q(
            visibility=SavedMovie.Visibility.SHARED,
            pk__in=SavedMovie.shared_with.through.objects.filter(user=user).values(
                "savedmovie"
            ),
        )
        return self.filter(models.Q(owner=user) | public | shared_with_user)

    def community_for(self, user):
        """Community: other users' entries ``user`` may view.

        Shared by the website's Community page and the API's community scope.
        """
        queryset = self.visible_to(user)
        if user and user.is_authenticated:
            queryset = queryset.exclude(owner=user)
        return queryset

    def editable_by(self, user):
        """Entries ``user`` may edit or delete: the owner and staff only."""
        if is_staff_user(user):
            return self.all()
        if not user or not user.is_authenticated:
            return self.none()
        return self.filter(owner=user)


class SavedMovie(models.Model):
    """A movie in one user's library."""

    class Status(models.TextChoices):
        WANT_TO_RENT = "want", "Want to rent"
        RENTED = "rented", "Rented"
        WATCHED = "watched", "Watched"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"
        SHARED = "shared", "Shared"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_movies",
    )
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="saves")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.WANT_TO_RENT
    )
    rented_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    notes = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="shared_saved_movies"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SavedMovieQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "movie"], name="unique_saved_movie_per_owner"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__isnull=True)
                | models.Q(rating__gte=1, rating__lte=5),
                name="saved_movie_rating_1_to_5",
            ),
        ]

    def __str__(self):
        return f"{self.movie} – {self.owner}"

    def get_absolute_url(self):
        return reverse("rentals:saved_detail", args=[self.pk])

    def change_status(self, status, rental_days=DEFAULT_RENTAL_DAYS):
        """Apply the rental rules for a status change (does not save).

        Setting Rented (again) starts a fresh rental of ``rental_days`` days.
        Any other status ends the rental: ``due_at`` is cleared and
        ``rented_at`` is kept as "last rented" history.
        """
        self.status = status
        if status == self.Status.RENTED:
            self.rented_at = timezone.now()
            self.due_at = self.rented_at + timedelta(days=int(rental_days))
        else:
            self.due_at = None

    @property
    def rental_days(self):
        """Length of the current rental in whole days, or None if not rented."""
        if self.status != self.Status.RENTED or not (self.rented_at and self.due_at):
            return None
        return (self.due_at - self.rented_at).days

    def change_rental_length(self, rental_days):
        """Fix the length of the current rental, keeping its start date."""
        if self.status == self.Status.RENTED and self.rented_at:
            self.due_at = self.rented_at + timedelta(days=int(rental_days))

    def can_edit(self, user):
        """True for the owner and staff (same rule as ``editable_by``)."""
        return bool(
            is_staff_user(user)
            or (user and user.is_authenticated and user.pk == self.owner_id)
        )

    @property
    def is_overdue(self):
        """Rented and due before today. A rental due today is not overdue."""
        return bool(
            self.status == self.Status.RENTED
            and self.due_at
            and timezone.localdate(self.due_at) < timezone.localdate()
        )

    @property
    def stars(self):
        """The rating as five stars, e.g. ``★★★☆☆``; empty when unrated."""
        if not self.rating:
            return ""
        return "★" * self.rating + "☆" * (5 - self.rating)
