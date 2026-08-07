# Adding New Endpoints

When implementing new features with new endpoints, follow this pattern:

1. Create a new module under `app/api/` (one file per feature/domain area) that exposes its
   own `APIRouter`.
2. Use FastAPI metadata (`summary=`, `tags=`, `response_model=`, `responses={...}`) so the
   endpoints are self-documenting in OpenAPI (`/docs`).
3. Use **Pydantic v2 models** for request/response bodies — validation is automatic and
   validation failures return an RFC 9457 `application/problem+json` response via the global
   handler in `app/problem_details.py`.
4. Include the feature router on the versioned group in `app/api/v1.py`.

**Example pattern (`app/api/widgets.py`):**

```python
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/widgets", tags=["widgets"])


class Widget(BaseModel):
    id: int
    name: str


@router.get("", summary="List widgets", response_model=list[Widget])
async def list_widgets() -> list[Widget]:
    return [Widget(id=1, name="example")]
```

Then include it on the versioned group in `app/api/v1.py`:

```python
from app.api import widgets

router.include_router(widgets.router)  # -> /api/v1/widgets
```

Key conventions:

- One file per feature/domain area, each exposing its own `APIRouter`.
- Mount everything on the versioned `/api/v1` group so URLs stay stable and grouped.
- Prefer typed Pydantic models over raw dicts for compile-time and runtime safety.
- Declare non-2xx responses with `responses={401: ..., 404: ...}` for accurate OpenAPI.
- The versioned group is **unauthenticated** in the baseline scaffold. An auth skill
  (for example `veracity-auth-python`) adds an auth dependency to the group and marks
  specific public endpoints anonymous.
