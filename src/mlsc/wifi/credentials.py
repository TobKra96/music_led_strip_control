"""The Hotspot's SSID and password. The password is chosen by the user, or generated once and written to the boot partition."""
from __future__ import annotations

import secrets
from collections.abc import Callable
from pathlib import Path

from loguru import logger

USER_PASSWORD_FILE = "mlsc-hotspot-password.txt"  # ruff: ignore[hardcoded-password-string]
GENERATED_FILE = "mlsc-hotspot.txt"
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 63
GENERATED_PASSWORD_BYTES = 9
SSID_PREFIX = "MLSC-"
FALLBACK_SSID_SUFFIX = "0000"


def _valid(password: str) -> bool:
    return MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH


class HotspotCredentials:
    """`boot_dir` is None where there is no boot partition (Windows, WSL); the generated password then lives for this run only."""

    def __init__(self, boot_dir: Path | None, mac: Callable[[], str | None]) -> None:
        self._boot_dir = boot_dir
        self._mac = mac
        self._generated: str | None = None

    def ssid(self) -> str:
        digits = (self._mac() or "").replace(":", "").replace("-", "")
        return SSID_PREFIX + (digits[-4:].upper() if len(digits) >= 4 else FALLBACK_SSID_SUFFIX)

    def password(self) -> str:
        return self._user_password() or self._stored_password() or self._generate()

    def _read(self, name: str) -> str | None:
        if self._boot_dir is None:
            return None
        try:
            return (self._boot_dir / name).read_text(encoding="utf-8")
        except OSError:
            return None

    def _user_password(self) -> str | None:
        text = self._read(USER_PASSWORD_FILE)
        password = text.strip() if text else ""
        if text is not None and not _valid(password):
            logger.warning("{} must hold {} to {} characters; it is ignored.", USER_PASSWORD_FILE, MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH)
        return password if _valid(password) else None

    def _stored_password(self) -> str | None:
        for line in (self._read(GENERATED_FILE) or "").splitlines():
            key, _, value = line.partition(":")
            if key.strip().lower() == "password" and _valid(value.strip()):
                return value.strip()
        return self._generated

    def _generate(self) -> str:
        self._generated = secrets.token_urlsafe(GENERATED_PASSWORD_BYTES)
        if self._boot_dir is not None:
            try:
                (self._boot_dir / GENERATED_FILE).write_text(
                    f"MLSC Hotspot\nSSID: {self.ssid()}\nPassword: {self._generated}\n", encoding="utf-8")
            except OSError as e:
                logger.warning("The Hotspot password could not be written to {}: {}", self._boot_dir / GENERATED_FILE, e)
        return self._generated
