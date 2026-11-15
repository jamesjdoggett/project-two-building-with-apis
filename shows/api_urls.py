from django.urls import path

from .api import EntryDetail, EntryList, EntryRefresh

app_name = "api"
urlpatterns = [
    path("entries/", EntryList.as_view(), name="entry-list"),
    path("entries/<int:pk>/", EntryDetail.as_view(), name="entry-detail"),
    path("entries/<int:pk>/refresh/", EntryRefresh.as_view(), name="entry-refresh"),
]
