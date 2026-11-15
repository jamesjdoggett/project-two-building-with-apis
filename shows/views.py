from urllib.parse import urlencode

import requests
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
    require_safe,
)
from django.views.decorators.vary import vary_on_headers

from .auth import login_required
from .forms import PersonalForm
from .library import SORT_CHOICES, library_entries
from .models import Entry
from .operations import SaveBusy, refresh_entry, save_entry
from .personal import PERSONAL_FIELDS, WATCH_STATUSES
from .tvmaze import ProviderError, RateLimited, ShowNotFound, search_shows


@login_required
@require_POST
def refresh(request, pk):
    entry = get_object_or_404(Entry.objects.filter(owner=request.user), pk=pk)
    if not action_form_valid(request):
        return render(
            request,
            "shows/detail.html",
            {
                "entry": entry,
                "error": "Submit this action using its form, with no extra fields.",
            },
            status=400,
        )
    try:
        entry = refresh_entry(request.user, pk)
    except Entry.DoesNotExist:
        raise Http404 from None
    except requests.Timeout:
        error, status = (
            "TVmaze timed out. Your saved data is unchanged. "
            "Try refreshing again later.",
            504,
        )
    except (RateLimited, SaveBusy) as exc:
        error, status = str(exc), 503
    except ProviderError as exc:
        error, status = (
            f"{exc} Your saved data is unchanged. Try refreshing again later.",
            502,
        )
    else:
        messages.success(
            request, "TVmaze metadata refreshed. Your viewing details are unchanged."
        )
        return redirect("shows:detail", pk=entry.pk)
    return render(
        request, "shows/detail.html", {"entry": entry, "error": error}, status=status
    )


def action_form_valid(request):
    return (
        request.content_type
        in {"application/x-www-form-urlencoded", "multipart/form-data"}
        and not (set(request.POST) - {"csrfmiddlewaretoken"})
        and not request.GET
        and not request.FILES
    )


@login_required
@require_http_methods(["GET", "POST"])
def delete(request, pk):
    entry = get_object_or_404(Entry.objects.filter(owner=request.user), pk=pk)
    if request.method == "POST":
        if not action_form_valid(request):
            return render(
                request,
                "shows/delete.html",
                {
                    "entry": entry,
                    "error": "Confirm deletion using this form, with no extra fields.",
                },
                status=400,
            )
        entry.delete()
        messages.success(
            request, "The entry and its personal data were permanently deleted."
        )
        return redirect("shows:library")
    return render(request, "shows/delete.html", {"entry": entry})


@login_required
@require_POST
def save_show(request, tvmaze_id):
    error = ""
    status = 400
    if (
        request.content_type
        not in {"application/x-www-form-urlencoded", "multipart/form-data"}
        or set(request.POST) - {"csrfmiddlewaretoken"}
        or request.GET
    ):
        error = "Save accepts only the selected TVmaze show ID, with no extra fields."
    else:
        try:
            entry, _ = save_entry(request.user, tvmaze_id)
            return redirect("shows:detail", pk=entry.pk)
        except requests.Timeout:
            error = "TVmaze timed out. Try saving again in a moment."
            status = 504
        except RateLimited as exc:
            error = str(exc)
            status = 503
        except SaveBusy as exc:
            error = str(exc)
            status = 503
        except ShowNotFound as exc:
            error = str(exc)
        except ProviderError as exc:
            error = str(exc)
            status = 502
        except ValueError as exc:
            error = str(exc)
    return render(
        request,
        "shows/save_error.html",
        {"error": error, "tvmaze_id": tvmaze_id},
        status=status,
    )


@login_required
@require_safe
def detail(request, pk):
    entry = get_object_or_404(Entry.objects.filter(owner=request.user), pk=pk)
    return render(request, "shows/detail.html", {"entry": entry})


@login_required
@require_http_methods(["GET", "POST"])
def edit(request, pk):
    entry = get_object_or_404(Entry.objects.filter(owner=request.user), pk=pk)
    initial = {field: getattr(entry, field) for field in PERSONAL_FIELDS}
    form = PersonalForm(
        request.POST if request.method == "POST" else None, initial=initial
    )
    if request.method == "POST":
        if (
            request.content_type
            not in {"application/x-www-form-urlencoded", "multipart/form-data"}
            or request.GET
            or request.FILES
        ):
            form.is_valid()
            form.add_error(
                None,
                "Submit personal changes using this form, with no query overrides.",
            )
        elif form.is_valid():
            for field in PERSONAL_FIELDS:
                setattr(entry, field, form.cleaned_data[field])
            entry.save(update_fields=[*PERSONAL_FIELDS, "updated_at"])
            messages.success(request, "Your viewing details were saved.")
            return redirect("shows:detail", pk=entry.pk)
    return render(
        request,
        "shows/edit.html",
        {"entry": entry, "form": form},
        status=400 if request.method == "POST" else 200,
    )


@login_required
@require_safe
def home(request):
    return redirect("shows:library")


@vary_on_headers("HX-Request")
@login_required
@require_safe
def library(request):
    entries, controls = library_entries(request.user, request.GET)
    page = Paginator(entries, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "shows/fragments/library.html"
        if request.headers.get("HX-Request") == "true"
        else "shows/library.html",
        {
            "page_obj": page,
            "query": controls["q"],
            "selected_status": controls["status"],
            "selected_sort": controls["sort"],
            "status_choices": WATCH_STATUSES,
            "sort_choices": SORT_CHOICES,
            "pagination_query": urlencode(controls),
            "has_entries": Entry.objects.filter(owner=request.user).exists(),
        },
    )


@vary_on_headers("HX-Request")
@login_required
@require_safe
def discover(request):
    query = request.GET.get("q", "").strip()
    results = []
    error = ""
    if query:
        try:
            results = search_shows(query)
        except requests.Timeout:
            error = "TVmaze timed out. Try again in a moment."
        except ProviderError as exc:
            error = str(exc)
    elif "q" in request.GET:
        error = "Enter a show title before searching TVmaze."
    saved_ids = set(
        Entry.objects.filter(
            owner=request.user, tvmaze_id__in=[show.tvmaze_id for show in results]
        ).values_list("tvmaze_id", flat=True)
    )
    return render(
        request,
        "shows/fragments/discover.html"
        if request.headers.get("HX-Request") == "true"
        else "shows/discover.html",
        {
            "query": query,
            "results": results,
            "error": error,
            "searched": bool(query) and not error,
            "saved_ids": saved_ids,
        },
    )
