"""Core httpx auth layer injects the bearer token and subscription key."""

from __future__ import annotations

import httpx

from veracity_core.apiclient import BEARER_PREFIX, VeracityAuth


def test_veracity_auth_injects_headers():
    auth = VeracityAuth(token_provider=lambda: "test-access-token", subscription_key="sub-key-123")
    request = httpx.Request("GET", "https://api.veracity.com/veracity/graph/v4/my/profile")
    prepared = next(auth.auth_flow(request))
    assert prepared.headers["Authorization"] == BEARER_PREFIX + "test-access-token"
    assert prepared.headers["Ocp-Apim-Subscription-Key"] == "sub-key-123"


def test_veracity_auth_omits_missing_subscription_key():
    auth = VeracityAuth(token_provider=lambda: "tok", subscription_key="")
    request = httpx.Request("GET", "https://api.veracity.com/veracity/graph/v4/my/profile")
    prepared = next(auth.auth_flow(request))
    assert prepared.headers["Authorization"] == BEARER_PREFIX + "tok"
    assert "Ocp-Apim-Subscription-Key" not in prepared.headers
