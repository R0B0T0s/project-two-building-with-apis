"""Re-fetch stale TMDB data and delete movies nobody has saved.

TMDB's terms allow cached data to be kept for at most six months. Run this by
hand (``uv run python manage.py refresh_movies``); a real deployment would
schedule it.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from rentals import services, tmdb
from rentals.models import Movie

logger = logging.getLogger(__name__)

# TMDB allows caching for six months; refresh a little before that.
REFRESH_AFTER = timedelta(days=150)


class Command(BaseCommand):
    help = (
        "Re-fetch movies fetched more than about five months ago, keeping the "
        "old data when TMDB fails, and delete movies with no saved entries."
    )

    def handle(self, *args, **options):
        # Delete orphans first, so TMDB is never called for a movie nobody saved.
        # delete() also counts the genre links it removes, so read Movie's count.
        _, per_model = Movie.objects.filter(saves__isnull=True).delete()
        deleted_movies = per_model.get(Movie._meta.label, 0)

        refreshed = failed = 0
        cutoff = timezone.now() - REFRESH_AFTER
        for movie in Movie.objects.filter(fetched_at__lt=cutoff).order_by("pk"):
            try:
                details = tmdb.get_movie_details(movie.tmdb_id)
            except tmdb.TMDBUnavailable as error:
                # Keep the existing data; the next run will try again.
                logger.warning(
                    "Could not refresh movie %s (TMDB %s): %s",
                    movie.pk,
                    movie.tmdb_id,
                    error,
                )
                self._say(
                    f"Kept existing data (TMDB failed): {movie}", self.style.WARNING
                )
                failed += 1
                continue
            movie = services.store_movie_details(details)
            self._say(f"Refreshed: {movie}")
            refreshed += 1

        self._say(
            f"Done. Refreshed {refreshed}, failed {failed}, "
            f"deleted {deleted_movies} unsaved movie(s).",
            self.style.SUCCESS,
        )

    def _say(self, text, style=None):
        """Write a line, replacing characters the console can't encode.

        A Windows console may not handle ★ or non-Latin titles; print "?"
        for those instead of crashing.
        """
        encoding = getattr(self.stdout, "encoding", None)
        if encoding:
            text = text.encode(encoding, errors="replace").decode(encoding)
        self.stdout.write(text, style)
