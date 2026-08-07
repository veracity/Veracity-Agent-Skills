"""Anonymous health views for Django — mirrors /health, /health/ready, /health/live."""

from __future__ import annotations

from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "healthy"})


def ready(request):
    return JsonResponse({"status": "ready"})


def live(request):
    return JsonResponse({"status": "alive"})
