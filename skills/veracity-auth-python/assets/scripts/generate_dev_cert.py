"""Generate the local HTTPS certificate/key pair used by the dev servers.

This removes the manual "run ``mkcert localhost`` and edit ``.env``" step: the cert
paths already live in ``.env`` (``HTTPS_CERT_FILE`` / ``HTTPS_KEY_FILE``, defaulting to
``.certs/localhost.pem`` and ``.certs/localhost-key.pem``), so this helper simply
materialises files at those paths.

Order of preference:

1. **mkcert** — when the ``mkcert`` binary is on ``PATH`` we use it, because it produces a
   certificate that is trusted by the OS/browser (no "your connection is not private"
   warning). ``mkcert -install`` is attempted best-effort so the local CA is trusted.
2. **cryptography fallback** — otherwise we generate a self-signed localhost certificate
   with the ``cryptography`` library (already available via ``pyjwt[crypto]``). Browsers
   will show a one-time trust prompt, but local HTTPS works out of the box with no extra
   tooling to install.

The helper is idempotent: if both files already exist it does nothing unless ``--force``
is passed. The dev launchers call :func:`ensure_dev_cert` automatically on startup, so a
plain ``uv run veracity-dev`` (or the Flask ``run_dev``) "just works".
"""

from __future__ import annotations

import argparse
import datetime as _dt
import ipaddress
import shutil
import subprocess
from pathlib import Path

try:  # settings are optional so the module can be imported/tested standalone
    from veracity_core.settings import Settings, get_settings
except ImportError:  # pragma: no cover - fallback when veracity_core isn't importable
    Settings = object  # type: ignore[assignment,misc]

    def get_settings():  # type: ignore[misc]
        raise RuntimeError("veracity_core.settings is not importable")


DEFAULT_HOSTS = ("localhost", "127.0.0.1", "::1")


def _resolve_paths(settings=None) -> tuple[Path, Path]:
    settings = settings or get_settings()
    return Path(settings.https_cert_file), Path(settings.https_key_file)


def _generate_with_mkcert(cert_file: Path, key_file: Path) -> bool:
    """Generate a trusted cert via mkcert. Returns True on success, False if unavailable."""
    if shutil.which("mkcert") is None:
        return False
    # Best-effort: install the local CA so the cert is trusted. Safe to re-run.
    subprocess.run(["mkcert", "-install"], check=False, capture_output=True)
    result = subprocess.run(
        [
            "mkcert",
            "-cert-file",
            str(cert_file),
            "-key-file",
            str(key_file),
            *DEFAULT_HOSTS,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"mkcert failed: {result.stderr.strip() or result.stdout.strip()}")
    return True


def _generate_self_signed(cert_file: Path, key_file: Path) -> None:
    """Fallback: self-signed localhost cert via the ``cryptography`` library."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])

    sans: list[x509.GeneralName] = []
    for host in DEFAULT_HOSTS:
        try:
            sans.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            sans.append(x509.DNSName(host))

    now = _dt.datetime.now(_dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _dt.timedelta(minutes=1))
        .not_valid_after(now + _dt.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(sans), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def ensure_dev_cert(settings=None, *, force: bool = False) -> tuple[Path, Path]:
    """Ensure the local HTTPS cert/key exist, generating them if needed.

    Returns the resolved ``(cert_file, key_file)`` paths. Idempotent: if both files
    already exist and ``force`` is False, the existing files are left untouched.
    """
    cert_file, key_file = _resolve_paths(settings)

    if not force and cert_file.is_file() and key_file.is_file():
        return cert_file, key_file

    for path in (cert_file, key_file):
        path.parent.mkdir(parents=True, exist_ok=True)

    if _generate_with_mkcert(cert_file, key_file):
        print(f"Generated trusted localhost certificate via mkcert -> {cert_file}, {key_file}")
    else:
        _generate_self_signed(cert_file, key_file)
        print(
            "mkcert not found; generated a self-signed localhost certificate via "
            f"cryptography -> {cert_file}, {key_file}"
        )
    return cert_file, key_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate the certificate even if it already exists.",
    )
    args = parser.parse_args()
    ensure_dev_cert(force=args.force)


if __name__ == "__main__":
    main()
