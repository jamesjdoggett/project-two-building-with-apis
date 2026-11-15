from functools import wraps

from django.contrib.auth.decorators import login_required as django_login_required
from django.http import HttpResponse


def login_required(view):
    protected = django_login_required(view)

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        response = protected(request, *args, **kwargs)
        if (
            not request.user.is_authenticated
            and request.headers.get("HX-Request") == "true"
            and response.status_code == 302
        ):
            return HttpResponse(headers={"HX-Redirect": response.url})
        return response

    return wrapper
