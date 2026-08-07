"""Minimal Django settings for the reference test suite (pytest-django).

Uses the signed-cookie session backend so the OIDC BFF flow works without a database,
and wires the Veracity DRF authentication + security-headers middleware.
"""

from __future__ import annotations

SECRET_KEY = "test-only-insecure-secret"
DEBUG = True
ALLOWED_HOSTS = ["*", "testserver"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "veracity_django",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "veracity_django.middleware.VeracitySecurityHeadersMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "tests.django_urls"

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "veracity_django.jwt.VeracityJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "UNAUTHENTICATED_USER": None,
}

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
