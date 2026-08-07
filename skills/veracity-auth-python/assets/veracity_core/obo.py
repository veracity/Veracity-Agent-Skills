"""MSAL token acquisition for downstream Veracity API calls (framework-agnostic).

Two providers, matching the .NET skill:

  * ``build_obo_token_provider`` — on-behalf-of exchange for an **OIDC BFF** app: turns
    the signed-in user's token into one scoped to the Veracity ``user_impersonation``
    scope, so calls are made *as the user*.
  * ``build_client_credentials_token_provider`` — for a **JWT Bearer** API that must call
    the Veracity API *as itself* (app-only), not on behalf of a user.

MSAL caches and refreshes tokens, so repeated calls are cheap. For multi-instance
deployments back the MSAL token cache with Redis (see references/oidc.md).
"""

from __future__ import annotations

from typing import Callable

import msal

from veracity_core.constants import VERACITY_AUTHORITY
from veracity_core.settings import Settings

# A callable returning a valid downstream access token.
TokenProvider = Callable[[], str]


def build_obo_token_provider(settings: Settings, user_assertion: str) -> TokenProvider:
    """Return a provider that performs the MSAL on-behalf-of exchange for the Veracity scope.

    ``user_assertion`` is the access token from the user's session (OIDC login).
    """
    app = msal.ConfidentialClientApplication(
        client_id=settings.client_id,
        client_credential=settings.client_secret,
        authority=VERACITY_AUTHORITY,
    )

    def provider() -> str:
        result = app.acquire_token_on_behalf_of(
            user_assertion=user_assertion, scopes=[settings.veracity_scope]
        )
        if "access_token" not in result:
            raise RuntimeError(
                f"OBO token acquisition failed: {result.get('error_description', result)}"
            )
        return result["access_token"]

    return provider


def build_client_credentials_token_provider(settings: Settings) -> TokenProvider:
    """Return a provider that acquires an app-only token (client credentials)."""
    app = msal.ConfidentialClientApplication(
        client_id=settings.client_id,
        client_credential=settings.client_secret,
        authority=VERACITY_AUTHORITY,
    )

    def provider() -> str:
        result = app.acquire_token_for_client(scopes=[settings.veracity_scope])
        if "access_token" not in result:
            raise RuntimeError(
                f"Client-credentials token acquisition failed: "
                f"{result.get('error_description', result)}"
            )
        return result["access_token"]

    return provider
