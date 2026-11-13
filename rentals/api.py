"""The saved-entries API: list, retrieve, create, update and delete."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, pagination, status, viewsets

from . import tmdb
from .filters import CommunitySavedMovieFilter, SavedMovieFilter
from .models import SavedMovie
from .serializers import SavedMovieSerializer
from .views import PAGE_SIZE


class SavedMoviePagination(pagination.PageNumberPagination):
    """12 per page, with the website's rules for odd page numbers.

    Like ``Paginator.get_page`` on the website, a missing or bad page number
    gives page 1 and one past the end gives the last page (instead of DRF's
    default 404).
    """

    page_size = PAGE_SIZE

    def paginate_queryset(self, queryset, request, view=None):
        paginator = self.django_paginator_class(queryset, self.page_size)
        self.page = paginator.get_page(request.query_params.get(self.page_query_param))
        self.request = request
        if paginator.num_pages > 1 and self.template is not None:
            self.display_page_controls = True
        return list(self.page)


SCOPES = ("mine", "community")
WRITE_ACTIONS = ("update", "partial_update", "destroy")


class TMDBServiceUnavailable(exceptions.APIException):
    """503 for a create that needed TMDB while it was unavailable."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "tmdb_unavailable"

    @classmethod
    def from_error(cls, error):
        # The same wording as the website; the technical cause is only logged.
        if error.unreachable:
            return cls(
                "Couldn't reach TMDB, so the movie wasn't saved. Try again in a minute."
            )
        return cls(
            "Movie search is temporarily unavailable, so the movie wasn't saved. "
            "Try again later."
        )


class SavedMovieViewSet(viewsets.ModelViewSet):
    """Saved entries.

    List takes ``scope=mine`` (default, the caller's own entries) or
    ``scope=community`` (other users' entries the caller may see), plus the
    website's search, filter, ``sort`` and ``page`` parameters. Retrieve
    follows ``visible_to``. Signed-out callers can read Public entries.

    Create takes a ``tmdb_id`` plus optional status, ``rental_days``, rating,
    notes, visibility and ``shared_with`` usernames, and runs the website's
    save flow (503 if TMDB is unavailable). Update and delete follow
    ``editable_by`` (owner or staff; others get 404). Writes need sign-in (401).
    """

    serializer_class = SavedMovieSerializer
    pagination_class = SavedMoviePagination
    # The website's filter sets: search, filters and `sort` work the same.
    filter_backends = [DjangoFilterBackend]

    @property
    def scope(self):
        scope = self.request.query_params.get("scope") or "mine"
        if scope not in SCOPES:
            raise exceptions.ValidationError(
                {"scope": f"Must be one of: {', '.join(SCOPES)}."}
            )
        return scope

    @property
    def filterset_class(self):
        if self.action == "list" and self.scope == "community":
            return CommunitySavedMovieFilter
        return SavedMovieFilter

    def perform_create(self, serializer):
        try:
            serializer.save()
        except tmdb.TMDBUnavailable as error:
            raise TMDBServiceUnavailable.from_error(error) from None

    def get_queryset(self):
        user = self.request.user
        if self.action in WRITE_ACTIONS:
            # The single edit rule: owner or staff. Others get a 404, even
            # when they can view the entry.
            queryset = SavedMovie.objects.editable_by(user)
        elif self.action != "list":
            # The single view rule; anything else is a 404, not a 403.
            queryset = SavedMovie.objects.visible_to(user)
        elif self.scope == "community":
            queryset = SavedMovie.objects.community_for(user)
        elif user.is_authenticated:
            queryset = SavedMovie.objects.filter(owner=user)
        else:
            raise exceptions.NotAuthenticated(
                "Sign in to list your own entries, or use scope=community "
                "to list Public entries."
            )
        return queryset.select_related("movie", "owner").prefetch_related(
            "movie__genres", "shared_with"
        )
