"""HTTPS-first local development server for the Veracity FastAPI reference app."""

from __future__ import annotations

from pathlib import Path

import uvicorn

from app.settings import Settings, get_settings


def build_uvicorn_kwargs(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or get_settings()

    cert_file = Path(settings.https_cert_file)
    key_file = Path(settings.https_key_file)
    missing = [str(path) for path in (cert_file, key_file) if not path.is_file()]
    if missing:
        raise RuntimeError(
            "Local HTTPS requires HTTPS_CERT_FILE and HTTPS_KEY_FILE to point to existing files. "
            "Generate a trusted localhost certificate (for example with mkcert) and update .env."
        )

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
