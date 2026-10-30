"""A scriptable WifiManager for tests and UI development on hosts without NetworkManager."""
from __future__ import annotations

import secrets
from collections.abc import Iterable
from dataclasses import dataclass

from mlsc.wifi.manager import CLIENT, HOTSPOT, Capabilities, HotspotInfo, Network, WifiError, WifiManager, WifiStatus

MOCK_IP = "192.168.1.50"
DEFAULT_HOTSPOT_SSID = "MLSC-0000"
GENERATED_PASSWORD_BYTES = 6


@dataclass(frozen=True)
class MockNetwork:
    ssid: str
    signal: int = 70
    security: str | None = "WPA2"
    password: str = ""


class MockWifiManager(WifiManager):
    def __init__(self, networks: Iterable[MockNetwork] = (), *, supported: bool = True, hotspot_supported: bool = True,
                 country: str | None = "DE", failing_connects: Iterable[str] = ()) -> None:
        self._networks = {network.ssid: network for network in networks}
        self._supported = supported
        self._hotspot_supported = hotspot_supported
        self._country = country
        self._failing_connects = set(failing_connects)
        self._known: set[str] = set()
        self._connected: str | None = None
        self._hotspot: HotspotInfo | None = None

    def capabilities(self) -> Capabilities:
        return Capabilities(self._supported, self._supported and self._hotspot_supported, self._country)

    def status(self) -> WifiStatus:
        if self._hotspot is not None:
            return WifiStatus(HOTSPOT, False, None, None, self._hotspot)
        return WifiStatus(CLIENT, self._connected is not None, self._connected, MOCK_IP if self._connected else None, None)

    def scan(self) -> list[Network]:
        if not self._supported:
            return []
        return [Network(n.ssid, n.signal, n.security, n.ssid == self._connected, n.ssid in self._known) for n in self._networks.values()]

    def connect(self, ssid: str, password: str | None) -> None:
        self._require_supported()
        network = self._networks.get(ssid)
        if network is None:
            msg = f"The network {ssid} was not found."
            raise WifiError(msg)
        if ssid in self._failing_connects or (network.security is not None and password != network.password):
            msg = f"Could not connect to {ssid}: check the password."
            raise WifiError(msg)
        self._hotspot = None
        self._known.add(ssid)
        self._connected = ssid

    def forget(self, ssid: str) -> None:
        self._require_supported()
        if ssid not in self._known:
            msg = f"The network {ssid} is not saved."
            raise WifiError(msg)
        self._known.discard(ssid)
        if self._connected == ssid:
            self._connected = None

    def start_hotspot(self, ssid: str | None, password: str | None) -> None:
        self._require_supported()
        if not self._hotspot_supported:
            msg = "The Wi-Fi adapter does not support the Hotspot."
            raise WifiError(msg)
        self._connected = None
        self._hotspot = HotspotInfo(ssid or DEFAULT_HOTSPOT_SSID, password or secrets.token_urlsafe(GENERATED_PASSWORD_BYTES))

    def stop_hotspot(self) -> None:
        self._hotspot = None

    def _require_supported(self) -> None:
        if not self._supported:
            msg = "Wi-Fi management is not supported on this host."
            raise WifiError(msg)
