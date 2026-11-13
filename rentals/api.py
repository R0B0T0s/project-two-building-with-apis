"""The saved-entries API. Read-only for now (list and retrieve)."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, pagination, viewsets

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


class SavedMovieViewSet(viewsets.ReadOnlyModelViewSet):
    """Saved entries.

    List takes ``scope=mine`` (default, the caller's own entries) or
    ``scope=community`` (other users' entries the caller may see), plus the
    website's search, filter, ``sort`` and ``page`` parameters. Retrieve
    follows ``visible_to``. Signed-out callers can read Public entries.
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

    def get_queryset(self):
        user = self.request.user
        if self.action != "list":
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
