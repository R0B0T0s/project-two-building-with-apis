"""All calls to the TMDB API go through this module.

Every failure becomes a single ``TMDBUnavailable`` exception. The technical cause
is written to the server log; callers only show a friendly message.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

API_ROOT = "https://api.themoviedb.org/3"
SEARCH_URL = f"{API_ROOT}/search/movie"
MOVIE_URL = f"{API_ROOT}/movie/{{tmdb_id}}"
TIMEOUT_SECONDS = 10


class TMDBUnavailable(Exception):
    """TMDB could not be used. ``unreachable`` is True for timeouts and lost connections."""

    def __init__(self, message, *, unreachable=False):
        super().__init__(message)
        self.unreachable = unreachable


def _get(url, params=None):
    """GET a TMDB URL and return the decoded JSON, or raise TMDBUnavailable."""
    headers = {
        "Authorization": f"Bearer {settings.TMDB_READ_TOKEN}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(
            url, params=params, headers=headers, timeout=TIMEOUT_SECONDS
        )
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
        logger.warning("TMDB unreachable for %s: %r", url, error)
        raise TMDBUnavailable("TMDB unreachable", unreachable=True) from error
    except requests.exceptions.RequestException as error:
        logger.error("TMDB request to %s failed: %r", url, error)
        raise TMDBUnavailable("TMDB request failed") from error

    if not response.ok:
        logger.error(
            "TMDB returned status %s for %s: %s",
            response.status_code,
            url,
            response.text[:200],
        )
        raise TMDBUnavailable(f"TMDB returned status {response.status_code}")

    try:
        return response.json()
    except ValueError as error:
        logger.error("TMDB sent unreadable JSON for %s: %r", url, error)
        raise TMDBUnavailable("TMDB sent unreadable JSON") from error


def search_movies(query, page=1):
    """Search TMDB movies by title.

    Returns ``{"results": [...], "page": int, "total_pages": int}``.
    """
    data = _get(
        SEARCH_URL, params={"query": query, "page": page, "include_adult": "false"}
    )
    return {
        "results": data.get("results", []),
        "page": data.get("page", page),
        "total_pages": data.get("total_pages", 0),
    }


def get_movie_details(tmdb_id):
    """Return TMDB's details for one movie (title, release date, genres, ...)."""
    return _get(MOVIE_URL.format(tmdb_id=int(tmdb_id)))
