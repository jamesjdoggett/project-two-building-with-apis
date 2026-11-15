import requests
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_safe

from .models import Entry
from .operations import SaveBusy, save_entry
from .tvmaze import ProviderError, RateLimited, ShowNotFound, search_shows


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
@require_safe
def home(request):
    return redirect("shows:library")


@login_required
@require_safe
def library(request):
    entries = Entry.objects.filter(owner=request.user)
    page = Paginator(entries, 20).get_page(request.GET.get("page"))
    return render(request, "shows/library.html", {"page_obj": page})


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
        "shows/discover.html",
        {
            "query": query,
            "results": results,
            "error": error,
            "searched": bool(query) and not error,
            "saved_ids": saved_ids,
        },
    )
