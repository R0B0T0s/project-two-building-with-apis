from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("api/", include("rentals.api_urls")),
    # Log in / log out links for DRF's browsable API.
    path("api-auth/", include("rest_framework.urls")),
    path("", include("rentals.urls")),
]
