from django import forms
from django.contrib.auth import get_user_model

from .models import DEFAULT_RENTAL_DAYS, RENTAL_DAY_CHOICES, SavedMovie

User = get_user_model()

RATING_CHOICES = [("", "Not rated")] + [
    (n, f"{'★' * n}{'☆' * (5 - n)}  ({n} star{'s' if n > 1 else ''})")
    for n in range(1, 6)
]


class SavedMovieForm(forms.ModelForm):
    """Edit page form. Status changes go through the model's rental rules."""

    rental_days = forms.TypedChoiceField(
        label="Rental length",
        choices=RENTAL_DAY_CHOICES,
        coerce=int,
        initial=DEFAULT_RENTAL_DAYS,
        help_text="When you change the status to Rented, the rental starts now "
        "and is due after this many days. Changing it on a current rental moves "
        "the due date and keeps the start date.",
    )
    rating = forms.TypedChoiceField(
        label="Your rating",
        choices=RATING_CHOICES,
        coerce=int,
        empty_value=None,
        required=False,
        help_text="Optional, at any status.",
    )
    shared_usernames = forms.CharField(
        label="Shared with",
        required=False,
        help_text="Usernames separated by commas. Used only when visibility is Shared.",
    )

    class Meta:
        model = SavedMovie
        fields = ["status", "rating", "notes", "visibility"]
        labels = {"notes": "Notes", "visibility": "Who can see this"}
        help_texts = {
            "notes": "A reminder for yourself, or your review. Your notes follow "
            "the visibility below: on a Public entry they are a public review.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.instance.status
        # Open on the current rental's length, so the form shows the truth and
        # a notes-only edit leaves the rental alone.
        if self.instance.rental_days in dict(RENTAL_DAY_CHOICES):
            self.initial["rental_days"] = self.instance.rental_days
        if self.instance.pk:
            self.initial["shared_usernames"] = ", ".join(
                self.instance.shared_with.order_by("username").values_list(
                    "username", flat=True
                )
            )

    def clean_shared_usernames(self):
        """Turn "alice, bob" into a list of User objects."""
        raw = self.cleaned_data["shared_usernames"]
        names = {name.strip() for name in raw.split(",") if name.strip()}
        users = list(User.objects.filter(username__in=names))
        unknown = sorted(names - {user.username for user in users})
        if unknown:
            raise forms.ValidationError(
                "No user with the username %(names)s. Check the spelling: "
                "usernames are case-sensitive.",
                params={"names": ", ".join(unknown)},
                code="unknown_username",
            )
        return users

    def clean(self):
        cleaned = super().clean()
        shared_with = cleaned.get("shared_usernames")
        if (
            cleaned.get("visibility") == SavedMovie.Visibility.SHARED
            and shared_with is not None  # None: already rejected as unknown
            and not shared_with
        ):
            self.add_error(
                "shared_usernames",
                "Add at least one username to share with, or choose Private.",
            )
        return cleaned

    def save(self, commit=True):
        saved = super().save(commit=False)
        new_status = self.cleaned_data["status"]
        rental_days = self.cleaned_data["rental_days"]
        # Only an actual status change starts or ends a rental, so editing the
        # notes of a rented movie doesn't reset its due date.
        if new_status != self._original_status:
            saved.change_status(new_status, rental_days)
        elif "rental_days" in self.changed_data:
            # Still Rented with a new length: move the due date, keep the start.
            saved.change_rental_length(rental_days)
        if commit:
            saved.save()
            self.save_m2m()
            saved.shared_with.set(self.cleaned_data["shared_usernames"])
        return saved
