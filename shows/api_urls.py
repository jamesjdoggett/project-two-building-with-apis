from django.urls import path

from .api import EntryDetail, EntryList

app_name = "api"
urlpatterns = [
    path("entries/", EntryList.as_view(), name="entry-list"),
    path("entries/<int:pk>/", EntryDetail.as_view(), name="entry-detail"),
]
