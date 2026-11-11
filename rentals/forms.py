from django import forms

from .models import DEFAULT_RENTAL_DAYS, RENTAL_DAY_CHOICES, SavedMovie

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

    class Meta:
        model = SavedMovie
        fields = ["status", "rating", "notes"]
        labels = {"notes": "Notes"}
        help_texts = {"notes": "A reminder for yourself, or your review."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.instance.status
        # Open on the current rental's length, so the form shows the truth and
        # a notes-only edit leaves the rental alone.
        if self.instance.rental_days in dict(RENTAL_DAY_CHOICES):
            self.initial["rental_days"] = self.instance.rental_days

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
        return saved
