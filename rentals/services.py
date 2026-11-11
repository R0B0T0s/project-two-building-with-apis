"""The save flow, shared by the website and (later) the API."""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import tmdb
from .models import Genre, Movie, SavedMovie

# TMDB allows caching for six months; reuse anything fetched more recently.
MOVIE_FRESH_FOR = timedelta(days=182)


class AlreadySaved(Exception):
    """The movie is already in this user's library."""

    def __init__(self, saved_movie):
        super().__init__("This movie is already in your library.")
        self.saved_movie = saved_movie


def get_or_fetch_movie(tmdb_id):
    """Return a fresh local Movie, fetching it from TMDB when needed.

    Raises ``tmdb.TMDBUnavailable`` if TMDB has to be called and fails.
    """
    tmdb_id = int(tmdb_id)
    movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    if movie and movie.fetched_at > timezone.now() - MOVIE_FRESH_FOR:
        return movie
    # Fetch before touching the database, so a TMDB failure saves nothing.
    details = tmdb.get_movie_details(tmdb_id)
    return store_movie_details(details)


def _release_year(release_date):
    try:
        return int((release_date or "")[:4])
    except ValueError:
        return None


@transaction.atomic
def store_movie_details(details):
    """Create or update the Movie and its Genres from a TMDB details response."""
    movie, _ = Movie.objects.update_or_create(
        tmdb_id=details["id"],
        defaults={
            "title": details.get("title") or "Untitled",
            "release_year": _release_year(details.get("release_date")),
            "overview": details.get("overview") or "",
            "poster_path": details.get("poster_path") or "",
            "fetched_at": timezone.now(),
        },
    )
    genres = []
    for item in details.get("genres") or []:
        genre, _ = Genre.objects.update_or_create(
            tmdb_id=item["id"], defaults={"name": item["name"]}
        )
        genres.append(genre)
    movie.genres.set(genres)
    return movie


def save_movie(user, tmdb_id):
    """Add a movie to ``user``'s library with the defaults (Want to rent, Private).

    Raises ``AlreadySaved`` for a duplicate and ``tmdb.TMDBUnavailable`` if the
    movie could not be fetched. Nothing is saved when either is raised.
    """
    existing = (
        SavedMovie.objects.filter(owner=user, movie__tmdb_id=int(tmdb_id))
        .select_related("movie")
        .first()
    )
    if existing:
        raise AlreadySaved(existing)

    movie = get_or_fetch_movie(tmdb_id)
    try:
        with transaction.atomic():
            return SavedMovie.objects.create(owner=user, movie=movie)
    except IntegrityError:
        # A double-click raced us; the unique constraint kept one entry.
        raise AlreadySaved(
            SavedMovie.objects.select_related("movie").get(owner=user, movie=movie)
        ) from None
