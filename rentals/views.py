from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import services, tmdb
from .forms import SavedMovieForm
from .models import DEFAULT_RENTAL_DAYS, SavedMovie

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
        movies = [_card(result) for result in data["results"]]
        # One query: which of these results are already in *this* user's library?
        saved_urls = {
            saved.movie.tmdb_id: saved.get_absolute_url()
            for saved in SavedMovie.objects.filter(
                owner=request.user,
                movie__tmdb_id__in=[movie["tmdb_id"] for movie in movies],
            ).select_related("movie")
        }
        for movie in movies:
            movie["saved_url"] = saved_urls.get(movie["tmdb_id"])

        context.update(
            movies=movies,
            page=page,
            total_pages=total_pages,
            prev_url=_find_url(query, page - 1) if page > 1 else None,
            next_url=_find_url(query, page + 1) if page < total_pages else None,
        )

    return render(request, "rentals/find.html", context)


def _find_url(query, page):
    return f"{reverse('rentals:find')}?{urlencode({'q': query, 'page': page})}"


@login_required
@require_POST
def save(request):
    """One-click save from the find page, then back to the same results."""
    query = request.POST.get("q", "").strip()
    page = _page_number(request.POST.get("page"))
    back = _find_url(query, page) if query else reverse("rentals:find")
    try:
        tmdb_id = int(request.POST.get("tmdb_id", ""))
    except ValueError:
        messages.error(request, "That movie couldn't be saved. Please try again.")
        return redirect(back)

    try:
        saved = services.save_movie(request.user, tmdb_id)
    except tmdb.TMDBUnavailable as error:
        # The technical cause is already logged by the service module.
        if error.unreachable:
            text = (
                "Couldn't reach TMDB, so the movie wasn't saved. Try again in a minute."
            )
        else:
            text = "Movie search is temporarily unavailable, so the movie wasn't saved."
        messages.error(request, text)
        return redirect(back)
    except services.AlreadySaved as duplicate:
        messages.info(
            request,
            format_html(
                '<strong>{}</strong> is already in your library. <a href="{}" '
                'class="alert-link">Edit details</a>',
                duplicate.saved_movie.movie.title,
                duplicate.saved_movie.get_absolute_url(),
            ),
        )
        return redirect(back)

    messages.success(
        request,
        format_html(
            "Saved <strong>{}</strong> to your library. "
            '<a href="{}" class="alert-link">Edit details</a>',
            saved.movie.title,
            saved.get_absolute_url(),
        ),
    )
    return redirect(back)


def _saved_list(request, queryset, *, community):
    """The one list view behind My Library and Community.

    The two pages differ only in their starting ``queryset`` (and whether
    cards show the owner). Everything renders from local data only.
    """
    saved_movies = list(queryset.select_related("movie", "owner"))
    for saved in saved_movies:
        saved.viewer_can_edit = saved.can_edit(request.user)
    return render(
        request,
        "rentals/saved_list.html",
        {"saved_movies": saved_movies, "community": community},
    )


@login_required
def library(request):
    """My Library: the signed-in user's own saved movies."""
    return _saved_list(
        request, SavedMovie.objects.filter(owner=request.user), community=False
    )


def community(request):
    """Community: other users' entries the viewer may see (open to everyone)."""
    queryset = SavedMovie.objects.visible_to(request.user)
    if request.user.is_authenticated:
        queryset = queryset.exclude(owner=request.user)
    return _saved_list(request, queryset, community=True)


def saved_detail(request, pk):
    """Full record for one saved movie, from local data only.

    Anyone ``visible_to`` excludes (including signed-out visitors on a
    non-Public entry) gets a 404, so the entry's existence isn't revealed.
    """
    queryset = SavedMovie.objects.visible_to(request.user).select_related(
        "movie", "owner"
    )
    saved = get_object_or_404(queryset, pk=pk)
    return render(
        request,
        "rentals/saved_detail.html",
        {"saved": saved, "can_edit": saved.can_edit(request.user)},
    )


def _get_editable(request, pk):
    """The entry if ``request.user`` may edit it (owner or staff), else 404.

    A 404 rather than a 403 avoids revealing Private entries to other users.
    """
    queryset = SavedMovie.objects.editable_by(request.user).select_related(
        "movie", "owner"
    )
    return get_object_or_404(queryset, pk=pk)


@login_required
def saved_edit(request, pk):
    saved = _get_editable(request, pk)
    form = SavedMovieForm(request.POST or None, instance=saved)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            format_html(
                "Saved your changes to <strong>{}</strong>.", saved.movie.title
            ),
        )
        return redirect(saved)
    return render(request, "rentals/saved_edit.html", {"saved": saved, "form": form})


@login_required
def saved_delete(request, pk):
    saved = _get_editable(request, pk)
    if request.method == "POST":
        title = saved.movie.title
        saved.delete()
        messages.success(
            request,
            format_html("Removed <strong>{}</strong> from the library.", title),
        )
        return redirect("rentals:library")
    return render(request, "rentals/saved_delete.html", {"saved": saved})


def _quick_status_change(request, pk, status, verb):
    saved = _get_editable(request, pk)
    saved.change_status(status, DEFAULT_RENTAL_DAYS)
    saved.save()
    messages.success(
        request, format_html("{} <strong>{}</strong>.", verb, saved.movie.title)
    )
    # Back to the list the card was on (My Library or Community), if safe.
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("rentals:library")


@login_required
@require_POST
def saved_rent(request, pk):
    """One-click Rent (2 days) from a library or Community card."""
    return _quick_status_change(
        request, pk, SavedMovie.Status.RENTED, f"Rented for {DEFAULT_RENTAL_DAYS} days:"
    )


@login_required
@require_POST
def saved_watched(request, pk):
    """One-click Mark watched from a library or Community card."""
    return _quick_status_change(
        request, pk, SavedMovie.Status.WATCHED, "Marked as watched:"
    )
