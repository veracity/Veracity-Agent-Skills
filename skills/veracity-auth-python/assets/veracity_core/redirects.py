"""Open-redirect guard (CWE-601) for the OIDC sign-in ``returnUrl`` (framework-agnostic).

The ``returnUrl`` accepted by ``/auth/challenge`` is caller-supplied and must never drive a
browser redirect without validation, otherwise an attacker can craft a link that phishes the
user off to an untrusted site after login. ``safe_return_url`` returns a guaranteed
application-relative path: anything absolute, protocol-relative (``//host``),
backslash-obfuscated, or scheme-bearing collapses to the safe ``fallback`` ("/").
"""

from __future__ import annotations


def safe_return_url(raw: str | None, fallback: str = "/") -> str:
    """Return ``raw`` when it is a safe root-relative path, otherwise ``fallback``."""
    if not isinstance(raw, str):
        return fallback
    value = raw.strip()
    # Must be a single-slash root-relative path.
    if not value.startswith("/"):
        return fallback
    # Block protocol-relative ("//host") and backslash-obfuscated ("/\host") forms.
    if value.startswith("//") or value.startswith("/\\"):
        return fallback
    if "\\" in value:
        return fallback
    # Reject control characters and any embedded scheme/host.
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        return fallback
    if "://" in value:
        return fallback
    return value
