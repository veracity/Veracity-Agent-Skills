"""Framework-agnostic Veracity Identity core.

This package holds the pieces that do NOT depend on any web framework, so the same
logic backs the FastAPI, Flask, and Django adapters:

  * constants  — Veracity B2C tenant + Platform API constants
  * settings   — pydantic-settings configuration model (shared by every framework)
  * tokens     — PyJWT validation, bearer extraction, Principal, AuthError
  * obo        — MSAL on-behalf-of / client-credentials token providers
  * apiclient  — httpx auth layer + V3/V4 client factories

Each web framework provides only a thin adapter (routing, session, middleware,
dependency/decorator) on top of this core.
"""

from __future__ import annotations
