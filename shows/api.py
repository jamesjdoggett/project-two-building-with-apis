"""Private session API over shared website operations and validation."""

import requests
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .library import library_entries
from .models import Entry
from .operations import SaveBusy, refresh_entry, save_entry
from .personal import MAX_BOOKMARK_NUMBER, PERSONAL_FIELDS, validate_personal_fields
from .tvmaze import ProviderError, RateLimited, ShowNotFound


class EntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entry
        exclude = ["owner"]
        read_only_fields = [field.name for field in Entry._meta.fields]


class StrictInput(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"detail": "Expected an object."})
        extra = set(data) - set(self.fields)
        if extra:
            raise serializers.ValidationError(
                {name: "This field is not writable." for name in sorted(extra)}
            )
        return super().to_internal_value(data)


class StrictInteger(serializers.IntegerField):
    def to_internal_value(self, data):
        if type(data) is not int:
            self.fail("invalid")
        return super().to_internal_value(data)


class CreateSerializer(StrictInput):
    tvmaze_id = StrictInteger(min_value=1, max_value=MAX_BOOKMARK_NUMBER)


class PersonalSerializer(StrictInput):
    # Preserve JSON types for the shared strict personal validation policy.
    rating = serializers.JSONField(allow_null=True)
    notes = serializers.JSONField()
    watch_status = serializers.JSONField()
    last_season = serializers.JSONField(allow_null=True)
    last_episode = serializers.JSONField(allow_null=True)

    def validate(self, attrs):
        state = {name: getattr(self.instance, name) for name in PERSONAL_FIELDS}
        state.update(attrs)
        try:
            validate_personal_fields(state)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from None
        return attrs

    def update(self, instance, validated_data):
        for name, value in validated_data.items():
            setattr(instance, name, value)
        if validated_data:
            instance.save(update_fields=[*validated_data, "updated_at"])
        return instance


def provider_failure(exc, *, creating=False):
    """Keep creation and refresh upstream contracts aligned without leaking data."""
    if isinstance(exc, requests.Timeout):
        return Response({"detail": "TVmaze timed out. Try again later."}, status=504)
    if isinstance(exc, (RateLimited, SaveBusy)):
        wait = exc.retry_after if isinstance(exc, RateLimited) else 1
        message = (
            str(exc)
            if isinstance(exc, RateLimited)
            else "The library is busy. Wait a moment, then retry."
        )
        return Response(
            {"detail": message, "retry_after": wait},
            status=503,
            headers={"Retry-After": str(wait)},
        )
    if creating and isinstance(exc, ShowNotFound):
        return Response(
            {"tvmaze_id": ["No available TVmaze show has this ID."]}, status=400
        )
    return Response(
        {"detail": "TVmaze returned unavailable or invalid data. Try again later."},
        status=502,
    )


class EntryList(APIView):
    def get(self, request):
        entries, controls = library_entries(request.user, request.query_params)
        page = Paginator(entries, 20).get_page(request.query_params.get("page"))
        return Response(
            {
                "count": page.paginator.count,
                "page": page.number,
                "pages": page.paginator.num_pages,
                "next": page.next_page_number() if page.has_next() else None,
                "previous": page.previous_page_number()
                if page.has_previous()
                else None,
                **controls,
                "results": EntrySerializer(page.object_list, many=True).data,
            }
        )

    def post(self, request):
        serializer = CreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            entry, created = save_entry(request.user, **serializer.validated_data)
        except (requests.Timeout, ProviderError, SaveBusy) as exc:
            return provider_failure(exc, creating=True)
        return Response(EntrySerializer(entry).data, status=201 if created else 200)


class EntryDetail(APIView):
    def delete(self, request, pk):
        entry = get_object_or_404(Entry, owner=request.user, pk=pk)
        validate_action(request)
        entry.delete()
        return Response(status=204)

    def get(self, request, pk):
        return Response(
            EntrySerializer(get_object_or_404(Entry, owner=request.user, pk=pk)).data
        )

    def put(self, request, pk):
        return self.update(request, pk, partial=False)

    def patch(self, request, pk):
        return self.update(request, pk, partial=True)

    def update(self, request, pk, *, partial):
        entry = get_object_or_404(Entry, owner=request.user, pk=pk)
        serializer = PersonalSerializer(entry, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(EntrySerializer(serializer.save()).data)


def validate_action(request):
    """Actions take no client metadata, ownership, URLs, or query overrides."""
    if request.query_params:
        raise serializers.ValidationError(
            {"detail": "This action takes no query parameters."}
        )
    StrictInput(data=request.data).is_valid(raise_exception=True)


class EntryRefresh(APIView):
    def post(self, request, pk):
        get_object_or_404(Entry, owner=request.user, pk=pk)
        validate_action(request)
        try:
            entry = refresh_entry(request.user, pk)
        except Entry.DoesNotExist:
            raise Http404 from None
        except (requests.Timeout, ProviderError, SaveBusy) as exc:
            return provider_failure(exc)
        return Response(EntrySerializer(entry).data)
