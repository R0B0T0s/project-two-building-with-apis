"""Consume the Movie Rental API from the command line.

Two behaviors:

    list    GET /api/saved/ with query parameters and print the results.
    update  PATCH one field of one saved entry, printing it before and after.

Start the dev server first (``uv run python manage.py runserver``), then, from
the repo root:

    uv run python scripts/api_client.py list
    uv run python scripts/api_client.py list --scope community --q alien --sort title
    uv run python scripts/api_client.py update 5 --notes "Family movie night pick"

``list --scope community`` works signed out (Public entries only). ``list
--scope mine`` and ``update`` need an account: pass ``--token`` (or set
``API_TOKEN``), or pass ``--username`` (or set ``API_USERNAME``) and the script
asks for the password (or reads ``API_PASSWORD``) and gets a token from
``/api/token/``.

This script talks to the API over HTTP only; it does not import the project.
"""

import argparse
import getpass
import os
import sys

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10  # seconds
SORT_CHOICES = [
    "saved_new",
    "saved_old",
    "title",
    "year_new",
    "year_old",
    "rating_high",
    "rating_low",
]
STATUS_CHOICES = ["want", "rented", "watched"]


class APIError(Exception):
    """A failed request, with a message ready to show the user."""


class MovieRentalAPI:
    """A small client for /api/saved/ and /api/token/."""

    def __init__(self, base_url, token=None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/json"
        if token:
            self.session.headers["Authorization"] = f"Token {token}"

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, timeout=TIMEOUT, **kwargs)
        except requests.exceptions.ConnectionError:
            raise APIError(
                f"Couldn't connect to {self.base_url}. Is the dev server running?"
            ) from None
        except requests.exceptions.Timeout:
            raise APIError(f"{method} {url} timed out after {TIMEOUT}s.") from None
        if not response.ok:
            raise APIError(
                f"{method} {url} -> {response.status_code}: {_body(response)}"
            )
        return response.json()

    def get_token(self, username, password):
        data = self._request(
            "POST", "/api/token/", data={"username": username, "password": password}
        )
        token = data["token"]
        self.session.headers["Authorization"] = f"Token {token}"
        return token

    def list_saved(self, params):
        return self._request("GET", "/api/saved/", params=params)

    def get_saved(self, entry_id):
        return self._request("GET", f"/api/saved/{entry_id}/")

    def update_saved(self, entry_id, fields):
        return self._request("PATCH", f"/api/saved/{entry_id}/", json=fields)


def _body(response):
    """The error detail from a response, JSON if possible."""
    try:
        return response.json()
    except ValueError:
        return response.text[:200]


# ---- Printing -------------------------------------------------------------


def format_entry(entry):
    """One saved entry as a few readable lines."""
    movie = entry["movie"]
    year = f" ({movie['release_year']})" if movie.get("release_year") else ""
    genres = ", ".join(genre["name"] for genre in movie.get("genres", [])) or "-"
    rating = (
        "★" * entry["rating"] + "☆" * (5 - entry["rating"])
        if entry["rating"]
        else "unrated"
    )
    lines = [
        f"#{entry['id']}  {movie['title']}{year}",
        f"    owner: {entry['owner']}   status: {entry['status']}   "
        f"visibility: {entry['visibility']}   rating: {rating}",
        f"    genres: {genres}",
    ]
    if entry.get("due_at"):
        overdue = "  (OVERDUE)" if entry.get("is_overdue") else ""
        lines.append(f"    due: {entry['due_at']}{overdue}")
    if entry.get("notes"):
        lines.append(f"    notes: {entry['notes']}")
    if "shared_with" in entry and entry["visibility"] == "shared":
        lines.append(f"    shared with: {', '.join(entry['shared_with']) or '-'}")
    return "\n".join(lines)


def print_list(data, params):
    shown = "&".join(f"{key}={value}" for key, value in params.items())
    print(f"GET /api/saved/?{shown}")
    print(f"{data['count']} matching entries (showing {len(data['results'])})\n")
    for entry in data["results"]:
        print(format_entry(entry))
        print()
    if data.get("next"):
        print(f"More results: {data['next']}")


# ---- Commands -------------------------------------------------------------


def authenticate(api, args, required):
    """Set up a token from --token, or from --username and a password."""
    if args.token:
        api.session.headers["Authorization"] = f"Token {args.token}"
        return
    if args.username:
        password = os.environ.get("API_PASSWORD") or getpass.getpass(
            f"Password for {args.username}: "
        )
        api.get_token(args.username, password)
        return
    if required:
        raise APIError(
            "This needs an account: pass --token, or --username (you'll be asked "
            "for the password). API_TOKEN / API_USERNAME / API_PASSWORD also work."
        )


def run_list(api, args):
    # Signed out, only the community scope works (the API gives 401 for "mine").
    authenticate(api, args, required=args.scope == "mine")
    params = {"scope": args.scope}
    for name in ("q", "status", "genre", "min_rating", "sort", "page"):
        value = getattr(args, name)
        if value is not None:
            params[name] = value
    if args.overdue:
        params["overdue"] = "true"
    print_list(api.list_saved(params), params)


def run_update(api, args):
    authenticate(api, args, required=True)
    field, value = (
        ("notes", args.notes) if args.notes is not None else ("rating", args.rating)
    )

    before = api.get_saved(args.id)
    print("BEFORE")
    print(format_entry(before))
    print()

    print(f"PATCH /api/saved/{args.id}/  {{{field!r}: {value!r}}}\n")
    after = api.update_saved(args.id, {field: value})

    print("AFTER")
    print(format_entry(after))
    print()
    print(f"{field}: {before[field]!r} -> {after[field]!r}")


def build_parser():
    parser = argparse.ArgumentParser(description="Consume the Movie Rental API.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("API_BASE_URL", DEFAULT_BASE_URL),
        help=f"API server (default {DEFAULT_BASE_URL}, or API_BASE_URL)",
    )
    parser.add_argument("--token", default=os.environ.get("API_TOKEN"))
    parser.add_argument("--username", default=os.environ.get("API_USERNAME"))
    commands = parser.add_subparsers(dest="command", required=True)

    list_cmd = commands.add_parser("list", help="List saved entries with filters.")
    list_cmd.add_argument("--scope", choices=["mine", "community"], default="community")
    list_cmd.add_argument("--q", help="search title or notes")
    list_cmd.add_argument("--status", choices=STATUS_CHOICES)
    list_cmd.add_argument("--genre", help="TMDB genre ID, e.g. 35 for Comedy")
    list_cmd.add_argument("--min-rating", type=int, choices=range(1, 6))
    list_cmd.add_argument("--overdue", action="store_true")
    list_cmd.add_argument("--sort", choices=SORT_CHOICES, default="title")
    list_cmd.add_argument("--page", type=int)
    list_cmd.set_defaults(handler=run_list)

    update_cmd = commands.add_parser("update", help="Change one field of an entry.")
    update_cmd.add_argument("id", type=int, help="saved entry ID")
    field = update_cmd.add_mutually_exclusive_group(required=True)
    field.add_argument("--notes", help="new notes text")
    field.add_argument("--rating", type=int, choices=range(1, 6), help="new rating 1-5")
    update_cmd.set_defaults(handler=run_update)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    api = MovieRentalAPI(args.base_url)
    try:
        args.handler(api, args)
    except APIError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
