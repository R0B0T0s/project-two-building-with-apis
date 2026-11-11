from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "rentals"

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("library/", views.library, name="library"),
    path("find/", views.find, name="find"),
    path("saved/new/", views.save, name="save"),
    path("saved/<int:pk>/", views.saved_detail, name="saved_detail"),
    path("saved/<int:pk>/edit/", views.saved_edit, name="saved_edit"),
    path("saved/<int:pk>/delete/", views.saved_delete, name="saved_delete"),
    path("saved/<int:pk>/rent/", views.saved_rent, name="saved_rent"),
    path("saved/<int:pk>/watched/", views.saved_watched, name="saved_watched"),
]
