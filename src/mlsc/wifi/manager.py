"""The WifiManager interface: what MLSC needs from the host's Wi-Fi, independent of the tool that provides it."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from mlsc.diagnosis import Diagnosis

CLIENT = "client"
HOTSPOT = "hotspot"


class WifiError(Exception):
    """A Wi-Fi change that could not be made. The message is meant for the user."""


@dataclass(frozen=True)
class Capabilities:
    supported: bool
    hotspot: bool
    country: str | None


@dataclass(frozen=True)
class HotspotInfo:
    ssid: str
    password: str | None


@dataclass(frozen=True)
class WifiStatus:
    mode: str
    connected: bool
    ssid: str | None
    ip: str | None
    hotspot: HotspotInfo | None


@dataclass(frozen=True)
class Network:
    ssid: str
    signal: int
    security: str | None
    in_use: bool
    known: bool


class WifiManager(ABC):
    @abstractmethod
    def capabilities(self) -> Capabilities:
        """What this host can do: Wi-Fi at all, Hotspot support and the regulatory country (None when unset)."""

    @abstractmethod
    def status(self) -> WifiStatus: ...

    @abstractmethod
    def scan(self) -> list[Network]: ...

    @abstractmethod
    def connect(self, ssid: str, password: str | None) -> None:
        """Join a network as a client. The password is handed to the system and never kept."""

    @abstractmethod
    def forget(self, ssid: str) -> None: ...

    @abstractmethod
    def start_hotspot(self, ssid: str | None, password: str | None) -> None:
        """Raise the Hotspot. A missing SSID or password is generated."""

    @abstractmethod
    def stop_hotspot(self) -> None: ...

    def diagnose(self) -> Diagnosis:
        capabilities = self.capabilities()
        if not capabilities.supported:
            return Diagnosis.warning("NetworkManager is not available, so MLSC cannot manage Wi-Fi.", "Install NetworkManager or manage Wi-Fi yourself.")
        if not capabilities.hotspot:
            return Diagnosis.warning("The Wi-Fi adapter does not support the Hotspot.", "Use a Wi-Fi adapter that supports the Hotspot.")
        if capabilities.country is None:
            return Diagnosis.warning("The Wi-Fi country is not set, so the radio may be blocked.", "Set it with: sudo raspi-config nonint do_wifi_country <CC>")
        return Diagnosis.ok(f"Wi-Fi is ready (country {capabilities.country}).")
