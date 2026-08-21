"""HTTPS-first local development server for the Veracity FastAPI reference app."""

from __future__ import annotations

from pathlib import Path

import uvicorn

from app.settings import Settings, get_settings


def build_uvicorn_kwargs(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or get_settings()

    cert_file = Path(settings.https_cert_file)
    key_file = Path(settings.https_key_file)
    if not (cert_file.is_file() and key_file.is_file()):
        # Auto-generate the localhost cert/key (mkcert when available, otherwise a
        # self-signed pair) so `veracity-dev` works without a manual setup step.
        from scripts.generate_dev_cert import ensure_dev_cert

        cert_file, key_file = ensure_dev_cert(settings)

    return {
        "app": "app.main:app",
        "host": settings.app_host,
        "port": settings.app_port,
        "reload": True,
        "ssl_certfile": str(cert_file),
        "ssl_keyfile": str(key_file),
    }


def main() -> None:
    uvicorn.run(**build_uvicorn_kwargs())
