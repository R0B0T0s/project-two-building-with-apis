"""API representation of saved entries, with the movie embedded read-only."""

from rest_framework import serializers

from .models import Genre, Movie, SavedMovie


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["tmdb_id", "name"]
        read_only_fields = fields


class MovieSerializer(serializers.ModelSerializer):
    """Shared TMDB data: only the server creates or updates it."""

    genres = GenreSerializer(many=True, read_only=True)
    poster_url = serializers.CharField(read_only=True)

    class Meta:
        model = Movie
        fields = [
            "tmdb_id",
            "title",
            "release_year",
            "overview",
            "poster_path",
            "poster_url",
            "genres",
            "fetched_at",
        ]
        read_only_fields = fields


class SavedMovieSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username", read_only=True)
    movie = MovieSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    shared_with = serializers.SlugRelatedField(
        slug_field="username", many=True, read_only=True
    )

    class Meta:
        model = SavedMovie
        fields = [
            "id",
            "owner",
            "movie",
            "status",
            "rented_at",
            "due_at",
            "is_overdue",
            "rating",
            "notes",
            "visibility",
            "shared_with",
            "created_at",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Like the detail page: only the owner and staff see who it's shared with.
        request = self.context.get("request")
        if not instance.can_edit(request.user if request else None):
            data.pop("shared_with")
        return data
