"""A minimal user-like object exposing a validated Veracity :class:`Principal`.

DRF's ``request.user`` and ``IsAuthenticated`` expect an object with
``is_authenticated``. This wraps the framework-agnostic Principal without touching the
Django ORM / auth user model — the API is stateless and does not create local users.
"""

from __future__ import annotations

from veracity_core.tokens import Principal


class VeracityUser:
    def __init__(self, principal: Principal) -> None:
        self.principal = principal
        self.id = principal.subject
        self.pk = principal.subject
        self.username = principal.subject
        self.name = principal.name
        self.claims = principal.claims

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def __str__(self) -> str:
        return self.username
