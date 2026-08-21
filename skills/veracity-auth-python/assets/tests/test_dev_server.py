import sys
from pathlib import Path

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


def test_build_uvicorn_kwargs_autogenerates_missing_certificates(tmp_path: Path):
    cert = tmp_path / ".certs" / "localhost.pem"
    key = tmp_path / ".certs" / "localhost-key.pem"
    settings = Settings(
        auth_strategy="jwt",
        https_cert_file=str(cert),
        https_key_file=str(key),
    )

    kwargs = build_uvicorn_kwargs(settings)

    # The dev launcher self-heals by generating the cert/key instead of erroring.
    assert cert.is_file()
    assert key.is_file()
    assert kwargs["ssl_certfile"] == str(cert)
    assert kwargs["ssl_keyfile"] == str(key)


def test_ensure_dev_cert_generates_valid_pem(tmp_path: Path):
    from cryptography import x509

    from scripts.generate_dev_cert import ensure_dev_cert

    cert = tmp_path / ".certs" / "localhost.pem"
    key = tmp_path / ".certs" / "localhost-key.pem"
    settings = Settings(auth_strategy="jwt", https_cert_file=str(cert), https_key_file=str(key))

    cert_path, key_path = ensure_dev_cert(settings)

    assert cert_path.is_file() and key_path.is_file()
    # Parses as a real certificate regardless of whether mkcert or the fallback ran.
    x509.load_pem_x509_certificate(cert_path.read_bytes())

    # Idempotent: a second call leaves the existing files untouched.
    first = cert_path.read_bytes()
    ensure_dev_cert(settings)
    assert cert_path.read_bytes() == first
