from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


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
