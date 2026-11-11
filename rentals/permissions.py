"""Role helpers shared by the website views and (later) the API permissions."""


def is_staff_user(user):
    """True for employees (``is_staff``) and admins (``is_superuser``)."""
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and (user.is_staff or user.is_superuser)
    )
