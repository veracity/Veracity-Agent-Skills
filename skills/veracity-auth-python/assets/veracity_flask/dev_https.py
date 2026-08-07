"""HTTPS-first local development runner for a Flask Veracity app.

Analog of the FastAPI ``veracity-dev`` launcher. For OIDC the BFF needs HTTPS locally so
the secure session cookie stays valid and the callback URL matches the app registration.
In production run behind gunicorn/uwsgi + a TLS-terminating reverse proxy instead.
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from veracity_core.settings import Settings, get_settings


def run_dev(app: Flask, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    cert_file = Path(settings.https_cert_file)
    key_file = Path(settings.https_key_file)
    missing = [str(p) for p in (cert_file, key_file) if not p.is_file()]
    if missing:
        raise RuntimeError(
            "Local HTTPS requires HTTPS_CERT_FILE and HTTPS_KEY_FILE to point to existing "
            "files. Generate a trusted localhost certificate (for example with mkcert) and "
            "update .env."
        )
    app.run(
        host=settings.app_host,
        port=settings.app_port,
        ssl_context=(str(cert_file), str(key_file)),
        debug=True,
    )


def main() -> None:
    from veracity_flask.app_factory import create_app

    run_dev(create_app())
