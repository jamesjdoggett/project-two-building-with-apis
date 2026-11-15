import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_safe

from .tvmaze import ProviderError, search_shows


@login_required
@require_safe
def home(request):
    return render(request, "shows/home.html")


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
    return render(
        request,
        "shows/discover.html",
        {
            "query": query,
            "results": results,
            "error": error,
            "searched": bool(query) and not error,
        },
    )
