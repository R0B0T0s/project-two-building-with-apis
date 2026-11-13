from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from .api import SavedMovieViewSet

app_name = "api"

router = DefaultRouter()
router.register("saved", SavedMovieViewSet, basename="saved")

urlpatterns = [
    path("token/", obtain_auth_token, name="token"),
    path("", include(router.urls)),
]
