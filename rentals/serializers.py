"""API representation of saved entries, with the movie embedded read-only."""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from . import services
from .models import DEFAULT_RENTAL_DAYS, RENTAL_DAY_CHOICES, Genre, Movie, SavedMovie

User = get_user_model()


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


class UsernameField(serializers.SlugRelatedField):
    """A user given by username, with the edit form's wording for unknown ones."""

    default_error_messages = {
        **serializers.SlugRelatedField.default_error_messages,
        "does_not_exist": "No user with the username {value}. Check the "
        "spelling: usernames are case-sensitive.",
    }

    def __init__(self, **kwargs):
        super().__init__(slug_field="username", **kwargs)


class SavedMovieSerializer(serializers.ModelSerializer):
    """A saved entry. Writes go through the website's save flow and rental rules.

    ``tmdb_id`` is write-only, required on create and ignored on update; the
    movie itself is embedded read-only. ``rental_days`` (1, 2 or 7, default 2)
    is write-only: it sets the length when the status changes to Rented, or
    moves the due date of a current rental.
    """

    owner = serializers.CharField(source="owner.username", read_only=True)
    movie = MovieSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    tmdb_id = serializers.IntegerField(write_only=True, required=False, min_value=1)
    rental_days = serializers.ChoiceField(
        choices=RENTAL_DAY_CHOICES, write_only=True, required=False
    )
    shared_with = UsernameField(
        many=True,
        required=False,
        queryset=User.objects.all(),
        help_text="Usernames. Used only when visibility is Shared.",
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
            "tmdb_id",
            "rental_days",
        ]
        read_only_fields = ["id", "rented_at", "due_at", "created_at"]

    def validate(self, attrs):
        if self.instance is None:
            self._validate_tmdb_id_on_create(attrs.get("tmdb_id"))
        else:
            # The movie is fixed once saved: tmdb_id is ignored on update.
            attrs.pop("tmdb_id", None)

        # Like the edit form: Shared needs at least one username.
        visibility = attrs.get(
            "visibility",
            self.instance.visibility
            if self.instance
            else SavedMovie.Visibility.PRIVATE,
        )
        if "shared_with" in attrs:
            has_usernames = bool(attrs["shared_with"])
        else:
            has_usernames = bool(self.instance and self.instance.shared_with.exists())
        if visibility == SavedMovie.Visibility.SHARED and not has_usernames:
            raise serializers.ValidationError(
                {
                    "shared_with": "Add at least one username to share with, "
                    "or choose Private."
                }
            )
        return attrs

    def _validate_tmdb_id_on_create(self, tmdb_id):
        if tmdb_id is None:
            raise serializers.ValidationError(
                {"tmdb_id": "This field is required when saving a movie."}
            )
        user = self.context["request"].user
        if SavedMovie.objects.filter(owner=user, movie__tmdb_id=tmdb_id).exists():
            raise serializers.ValidationError(
                {"tmdb_id": "This movie is already in your library."}
            )

    def create(self, validated_data):
        user = self.context["request"].user
        tmdb_id = validated_data.pop("tmdb_id")
        rental_days = validated_data.pop("rental_days", DEFAULT_RENTAL_DAYS)
        status = validated_data.pop("status", SavedMovie.Status.WANT_TO_RENT)
        shared_with = validated_data.pop("shared_with", [])
        # One transaction: if anything after the save fails, nothing is kept.
        try:
            with transaction.atomic():
                saved = services.save_movie(user, tmdb_id)
                for field, value in validated_data.items():
                    setattr(saved, field, value)
                saved.change_status(status, rental_days)
                saved.save()
                saved.shared_with.set(shared_with)
        except services.AlreadySaved:
            # A duplicate that raced past validate().
            raise serializers.ValidationError(
                {"tmdb_id": "This movie is already in your library."}
            ) from None
        return saved

    def update(self, instance, validated_data):
        status = validated_data.pop("status", instance.status)
        rental_days = validated_data.pop("rental_days", None)
        shared_with = validated_data.pop("shared_with", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        # The edit form's rules: only an actual status change starts or ends a
        # rental, so a notes-only edit of a rented movie keeps its due date.
        if status != instance.status:
            instance.change_status(status, rental_days or DEFAULT_RENTAL_DAYS)
        elif rental_days is not None:
            # Still Rented with a new length: move the due date, keep the start.
            instance.change_rental_length(rental_days)
        instance.save()
        if shared_with is not None:
            instance.shared_with.set(shared_with)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Like the detail page: only the owner and staff see who it's shared with.
        request = self.context.get("request")
        if not instance.can_edit(request.user if request else None):
            data.pop("shared_with")
        return data
