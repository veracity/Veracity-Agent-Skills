from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dev_server import build_uvicorn_kwargs
from app.settings import Settings


def test_build_uvicorn_kwargs_uses_https_files(tmp_path: Path):
    cert = tmp_path / "localhost.pem"
    key = tmp_path / "localhost-key.pem"
    cert.write_text("cert", encoding="utf-8")
    key.write_text("key", encoding="utf-8")

    kwargs = build_uvicorn_kwargs(
        Settings(
            app_host="localhost",
            app_port=54438,
            https_cert_file=str(cert),
            https_key_file=str(key),
        )
    )

    assert kwargs["app"] == "app.main:app"
    assert kwargs["host"] == "localhost"
    assert kwargs["port"] == 54438
    assert kwargs["reload"] is True
    assert kwargs["ssl_certfile"] == str(cert)
    assert kwargs["ssl_keyfile"] == str(key)


def test_build_uvicorn_kwargs_requires_existing_certificates():
    settings = Settings(
        https_cert_file=".certs/missing-cert.pem",
        https_key_file=".certs/missing-key.pem",
    )

    with pytest.raises(RuntimeError, match="Local HTTPS requires HTTPS_CERT_FILE and HTTPS_KEY_FILE"):
        build_uvicorn_kwargs(settings)
