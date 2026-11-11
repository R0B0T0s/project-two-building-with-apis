from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

from . import tmdb

POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342"
# TMDB serves at most 500 pages of search results.
MAX_TMDB_PAGE = 500


def _page_number(raw):
    try:
        page = int(raw)
    except TypeError, ValueError:
        return 1
    return min(max(page, 1), MAX_TMDB_PAGE)


def _card(result):
    """Turn a raw TMDB search result into what a poster card needs."""
    poster_path = result.get("poster_path")
    return {
        "tmdb_id": result.get("id"),
        "title": result.get("title") or "Untitled",
        "year": (result.get("release_date") or "")[:4],
        "overview": result.get("overview") or "",
        "poster_url": f"{POSTER_BASE_URL}{poster_path}" if poster_path else "",
    }


@login_required
def find(request):
    query = request.GET.get("q", "").strip()
    page = _page_number(request.GET.get("page"))
    context = {"query": query}

    if query:
        try:
            data = tmdb.search_movies(query, page=page)
        except tmdb.TMDBUnavailable as error:
            # The technical cause is already logged by the service module.
            context["tmdb_unreachable"] = error.unreachable
            context["tmdb_failed"] = True
            return render(request, "rentals/find.html", context)
        page = data["page"]
        total_pages = min(data["total_pages"], MAX_TMDB_PAGE)
        find_url = reverse("rentals:find")

        def page_url(number):
            return f"{find_url}?{urlencode({'q': query, 'page': number})}"

        context.update(
            movies=[_card(result) for result in data["results"]],
            page=page,
            total_pages=total_pages,
            prev_url=page_url(page - 1) if page > 1 else None,
            next_url=page_url(page + 1) if page < total_pages else None,
        )

    return render(request, "rentals/find.html", context)
