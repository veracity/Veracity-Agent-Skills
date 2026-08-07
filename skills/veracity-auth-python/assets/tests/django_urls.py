"""URL config for the Django reference tests: a DRF-protected sample view + adapter urls."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def drf_me(request):
    # Global DEFAULT_PERMISSION_CLASSES=IsAuthenticated enforces the bearer token;
    # request.user is the VeracityUser produced by VeracityJWTAuthentication.
    return Response({"id": request.user.principal.subject, "name": request.user.principal.name})


urlpatterns = [
    path("drf/me", drf_me),
    path("", include("veracity_django.urls")),
]
