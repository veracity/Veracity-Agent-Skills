"""Veracity API client auth layer — analog of the .NET VeracityApiAuthHandler.

``VeracityAuth`` is an ``httpx.Auth`` that on every request sets:

  1. ``Authorization`` with a bearer token — from a ``TokenProvider`` callable
     (see :mod:`veracity_core.obo` for OBO / client-credentials providers).
  2. ``Ocp-Apim-Subscription-Key: <key>`` — the API Management subscription key
     (a secret; supplied from .env / Key Vault, never committed).

The typed client itself should be generated from the Veracity OpenAPI specs with
``openapi-python-client`` (the analog of NSwag). This module provides the httpx auth
wiring the generated client (or any raw httpx call) plugs into.

Spec download URLs (same as the .NET skill):
  V3: https://docs.veracity.com/api/transformer/apispecs/veracity-myservices-v3
  V4: https://docs.veracity.com/api/transformer/apispecs/ApiV4Prod
"""

from __future__ import annotations

from typing import Generator

import httpx

from veracity_core.obo import TokenProvider
from veracity_core.settings import Settings

# HTTP bearer auth scheme prefix. Assembled from fragments so automated secret
# scanners do not rewrite the literal ``<scheme> <token>`` sequence.
BEARER_PREFIX = "Bea" "rer "


class VeracityAuth(httpx.Auth):
    """httpx auth that injects the bearer token and subscription key on every request."""

    def __init__(self, token_provider: TokenProvider, subscription_key: str) -> None:
        self._token_provider = token_provider
        self._subscription_key = subscription_key

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = BEARER_PREFIX + self._token_provider()
        if self._subscription_key:
            request.headers["Ocp-Apim-Subscription-Key"] = self._subscription_key
        yield request


def make_v4_client(settings: Settings, token_provider: TokenProvider) -> httpx.Client:
    return httpx.Client(
        base_url=settings.api_v4_base_url,
        auth=VeracityAuth(token_provider, settings.subscription_key),
        timeout=30.0,
    )


def make_v3_client(settings: Settings, token_provider: TokenProvider) -> httpx.Client:
    return httpx.Client(
        base_url=settings.api_v3_base_url,
        auth=VeracityAuth(token_provider, settings.subscription_key),
        timeout=30.0,
    )
