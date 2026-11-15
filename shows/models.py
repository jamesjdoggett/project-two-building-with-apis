from django.conf import settings
from django.db import models

from .personal import WATCH_STATUSES


class Entry(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tvmaze_id = models.PositiveBigIntegerField()
    title = models.TextField()
    source_url = models.URLField(max_length=2000)
    summary = models.TextField()
    genres = models.JSONField(default=list)
    language = models.TextField(blank=True)
    premiered = models.DateField(null=True, blank=True)
    ended = models.DateField(null=True, blank=True)
    provider_status = models.TextField(blank=True)
    poster_url = models.URLField(max_length=2000, blank=True)
    provider_name = models.CharField(max_length=20, default="TVmaze")
    license_url = models.URLField(
        default="https://creativecommons.org/licenses/by-sa/4.0/"
    )
    summary_transformation = models.TextField(
        default="Summaries converted from HTML to plain text."
    )
    retrieved_at = models.DateTimeField()
    rating = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    watch_status = models.CharField(
        max_length=9, choices=WATCH_STATUSES, default="planned"
    )
    last_season = models.BigIntegerField(null=True, blank=True)
    last_episode = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "tvmaze_id"], name="unique_owner_tvmaze"
            ),
            models.CheckConstraint(
                condition=models.Q(tvmaze_id__gt=0), name="positive_tvmaze_id"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__isnull=True)
                | models.Q(rating__range=(1, 10)),
                name="valid_personal_rating",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    watch_status__in=[value for value, _ in WATCH_STATUSES]
                ),
                name="valid_watch_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(last_season__isnull=True, last_episode__isnull=True)
                    | models.Q(
                        last_season__isnull=False,
                        last_episode__isnull=False,
                        last_season__gte=0,
                        last_episode__gte=1,
                    )
                ),
                name="valid_bookmark_pair",
            ),
        ]

    def __str__(self):
        return self.title
