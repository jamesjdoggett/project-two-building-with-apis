"""Private session API over shared website operations and validation."""

import requests
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .library import library_entries
from .models import Entry
from .operations import SaveBusy, save_entry
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
        except requests.Timeout:
            return Response(
                {"detail": "TVmaze timed out. Try again later."}, status=504
            )
        except RateLimited as exc:
            return Response(
                {"detail": str(exc), "retry_after": exc.retry_after},
                status=503,
                headers={"Retry-After": str(exc.retry_after)},
            )
        except ShowNotFound:
            return Response(
                {"tvmaze_id": ["No available TVmaze show has this ID."]}, status=400
            )
        except ProviderError:
            return Response(
                {
                    "detail": (
                        "TVmaze returned unavailable or invalid data. Try again later."
                    )
                },
                status=502,
            )
        except SaveBusy:
            return Response(
                {
                    "detail": "The library is busy. Wait a moment, then retry.",
                    "retry_after": 1,
                },
                status=503,
                headers={"Retry-After": "1"},
            )
        return Response(EntrySerializer(entry).data, status=201 if created else 200)


class EntryDetail(APIView):
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
