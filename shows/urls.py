from django.urls import path

from . import views

app_name = "shows"
urlpatterns = [
    path("", views.home, name="home"),
    path("library/", views.library, name="library"),
    path("discover/", views.discover, name="discover"),
    path("discover/<int:tvmaze_id>/save/", views.save_show, name="save"),
    path("library/<int:pk>/", views.detail, name="detail"),
    path("library/<int:pk>/edit/", views.edit, name="edit"),
]
