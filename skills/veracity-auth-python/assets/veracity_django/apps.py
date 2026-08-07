from __future__ import annotations

from django.apps import AppConfig


class VeracityAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "veracity_django"
    label = "veracity_django"
    verbose_name = "Veracity Identity"
