from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "rentals"

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("find/", views.find, name="find"),
    path("saved/new/", views.save, name="save"),
    path("saved/<int:pk>/", views.saved_detail, name="saved_detail"),
]
