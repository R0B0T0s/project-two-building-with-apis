from django.contrib import admin

from .models import Genre, Movie, SavedMovie

# Employee status (is_staff) is granted with the built-in User admin.


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["name", "tmdb_id"]
    search_fields = ["name"]


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ["title", "release_year", "tmdb_id", "fetched_at"]
    list_filter = ["genres"]
    search_fields = ["title", "tmdb_id"]
    filter_horizontal = ["genres"]


@admin.register(SavedMovie)
class SavedMovieAdmin(admin.ModelAdmin):
    list_display = ["movie", "owner", "status", "visibility", "rating", "due_at"]
    list_filter = ["status", "visibility", "rating"]
    search_fields = ["movie__title", "owner__username", "notes"]
    list_select_related = ["movie", "owner"]
    autocomplete_fields = ["owner", "movie"]
    filter_horizontal = ["shared_with"]
    readonly_fields = ["created_at"]
