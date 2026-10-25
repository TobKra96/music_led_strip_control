"""Optional HTTPS for the web interface, which browsers require before they allow microphone access on a LAN address.

Plain HTTP stays the default. Setting `general_settings.https_port` serves the same app on a second port with a self-signed
certificate through cheroot, a pure-Python server. Both libraries come with the `https` extra and are imported only here.
"""
from __future__ import annotations

import datetime as dt
import socket
import threading
from pathlib import Path

from loguru import logger

from mlsc import paths

CERTIFICATE_DAYS = 3650


def certificate_files() -> tuple[Path, Path]:
    directory = paths.data_dir() / "tls"
    return directory / "mlsc.crt", directory / "mlsc.key"


def ensure_certificate() -> tuple[Path, Path]:
    """Return the certificate and key, creating a self-signed pair on first use. Browsers ask to trust it once."""
    certificate, key = certificate_files()
    if certificate.exists() and key.exists():
        return certificate, key

    from cryptography import x509  # ruff: ignore[import-outside-top-level]
    from cryptography.hazmat.primitives import hashes, serialization  # ruff: ignore[import-outside-top-level]
    from cryptography.hazmat.primitives.asymmetric import ec  # ruff: ignore[import-outside-top-level]
    from cryptography.x509.oid import NameOID  # ruff: ignore[import-outside-top-level]

    hostname = socket.gethostname()
    private_key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name).public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=CERTIFICATE_DAYS))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname), x509.DNSName(f"{hostname}.local"), x509.DNSName("localhost")]), critical=False)
        .sign(private_key, hashes.SHA256())
    )
    certificate.parent.mkdir(parents=True, exist_ok=True)
    key.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    key.chmod(0o600)
    certificate.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    logger.info(f"Created a self-signed certificate for {hostname} in {certificate.parent}")
    return certificate, key


def start_https(app, port: int | None, http_port: int) -> threading.Thread | None:
    """Serve `app` over HTTPS on `port` in a background thread. Returns `None` when HTTPS is off or its extra is missing."""
    if not port:
        return None
    if port == http_port:
        logger.warning(f"https_port {port} is the same as webserver_port. HTTPS is not started.")
        return None
    try:
        from cheroot.ssl.builtin import BuiltinSSLAdapter  # ruff: ignore[import-outside-top-level]
        from cheroot.wsgi import Server  # ruff: ignore[import-outside-top-level]

        certificate, key = ensure_certificate()
    except ImportError:
        logger.warning("https_port is set but the https extra is missing. Install it with: pip install 'music-led-strip-control[https]'")
        return None

    server = Server(("0.0.0.0", port), app, numthreads=8)  # ruff: ignore[hardcoded-bind-all-interfaces]
    server.ssl_adapter = BuiltinSSLAdapter(str(certificate), str(key))
    thread = threading.Thread(target=server.safe_start, name="https-server", daemon=True)
    thread.start()
    logger.info(f"HTTPS is available on port {port}")
    return thread
