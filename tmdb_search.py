"""Search TMDB for movies from the console.

Usage:
    uv run tmdb_search.py

Needs TMDB_READ_TOKEN in a .env file (see .env.example).
"""

import os
import sys

import requests
from dotenv import load_dotenv

SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TIMEOUT_SECONDS = 10
MAX_RESULTS = 10
OVERVIEW_LENGTH = 80


def load_token():
    """Read the TMDB Read Access Token from .env, or exit with a helpful message."""
    load_dotenv()
    token = os.getenv("TMDB_READ_TOKEN", "").strip()
    if not token:
        sys.exit(
            "TMDB_READ_TOKEN not set - copy .env.example to .env and paste your "
            "Read Access Token (themoviedb.org > Settings > API)."
        )
    return token


def search_movies(session, phrase):
    """Return a list of movie dicts, or None if the request failed (message already printed)."""
    try:
        response = session.get(
            SEARCH_URL,
            params={"query": phrase, "include_adult": "false"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        print(f"TMDB took too long to respond (over {TIMEOUT_SECONDS}s). Try again.")
        return None
    except requests.exceptions.ConnectionError:
        print("Couldn't reach TMDB - check your internet connection.")
        return None
    except requests.exceptions.RequestException as error:
        print(f"Request failed: {error}")
        return None

    if response.status_code == 401:
        print("TMDB rejected the token - check it's the Read Access Token, not the API Key.")
        return None
    if response.status_code == 429:
        print("Rate limited by TMDB - wait a moment and try again.")
        return None
    if response.status_code >= 500:
        print(f"TMDB is having problems (status {response.status_code}) - try later.")
        return None
    if not response.ok:
        try:
            detail = response.json().get("status_message", "")
        except ValueError:
            detail = ""
        print(f"TMDB returned status {response.status_code}. {detail}".strip())
        return None

    try:
        return response.json().get("results", [])
    except ValueError:
        print("TMDB sent a response that couldn't be read as JSON.")
        return None


def show_results(phrase, movies):
    if not movies:
        print(f"No movies found for '{phrase}'.")
        return
    for number, movie in enumerate(movies[:MAX_RESULTS], start=1):
        year = (movie.get("release_date") or "")[:4] or "n/a"
        rating = movie.get("vote_average") or 0
        print(f"{number}. {movie.get('title', '?')} ({year})  ★ {rating:.1f}  [id {movie.get('id')}]")
        overview = movie.get("overview") or "(no overview)"
        if len(overview) > OVERVIEW_LENGTH:
            overview = overview[:OVERVIEW_LENGTH].rstrip() + "..."
        print(f"   {overview}")


def main():
    # Windows consoles/pipes may not support every character (e.g. ★ or non-Latin
    # titles); print a "?" for those instead of crashing.
    sys.stdout.reconfigure(errors="replace")
    token = load_token()
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})

    print("TMDB movie search. Press Enter on a blank line to quit.")
    while True:
        try:
            phrase = input("\nSearch movies: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not phrase:
            break
        movies = search_movies(session, phrase)
        if movies is not None:
            show_results(phrase, movies)
    print("Goodbye.")


if __name__ == "__main__":
    main()
