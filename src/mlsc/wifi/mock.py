"""A scriptable WifiManager for tests and UI development on hosts without NetworkManager."""
from __future__ import annotations

import secrets
from collections.abc import Iterable
from dataclasses import dataclass

from mlsc.wifi.hotspot_address import DEFAULT_HOTSPOT_ADDRESS
from mlsc.wifi.manager import (
    CLIENT,
    HOTSPOT,
    RADIO_NO_ADAPTER,
    RADIO_READY,
    RADIO_SWITCHED_OFF,
    Capabilities,
    HotspotInfo,
    Network,
    WifiError,
    WifiManager,
    WifiStatus,
    radio_problem,
)

MOCK_IP = "192.168.1.50"
MOCK_INTERFACE = "wlan0"
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
                 country: str | None = "DE", failing_connects: Iterable[str] = (), radio: str = RADIO_READY,
                 pinned_interface: str | None = None, radio_stuck: bool = False) -> None:
        self._networks = {network.ssid: network for network in networks}
        self._supported = supported
        self._hotspot_supported = hotspot_supported
        self._country = country
        self._failing_connects = set(failing_connects)
        self._radio = radio
        self._pinned = pinned_interface
        self._radio_stuck = radio_stuck
        self._known: set[str] = set()
        self._connected: str | None = None
        self._hotspot: HotspotInfo | None = None
        self.clients = 0
        self.networks_in_use: list[str] = []
        self.drop_on_failed_connect = False

    def capabilities(self) -> Capabilities:
        radio = RADIO_NO_ADAPTER if self._pinned not in {None, MOCK_INTERFACE} else self._radio
        return Capabilities(self._supported, self._supported and self._hotspot_supported, self._country, radio,
                            self._pinned or MOCK_INTERFACE, pinned=self._pinned is not None)

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
            if self.drop_on_failed_connect:
                self._connected = None
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

    def start_hotspot(self, ssid: str | None, password: str | None, address: str | None = None) -> None:
        self._require_supported()
        if not self._hotspot_supported:
            msg = "The Wi-Fi adapter does not support the Hotspot."
            raise WifiError(msg)
        self._connected = None
        self._hotspot = HotspotInfo(ssid or DEFAULT_HOTSPOT_SSID, password or secrets.token_urlsafe(GENERATED_PASSWORD_BYTES),
                                    address or DEFAULT_HOTSPOT_ADDRESS)

    def stop_hotspot(self) -> None:
        self._hotspot = None

    def connected_networks(self) -> list[str]:
        return list(self.networks_in_use)

    def hotspot_clients(self) -> int:
        return self.clients if self._hotspot is not None else 0

    def enable_radio(self) -> None:
        capabilities = self.capabilities()
        problem = radio_problem(capabilities)
        if problem is not None and capabilities.radio != RADIO_SWITCHED_OFF:
            raise WifiError(problem.message)
        if self._radio_stuck:
            msg = "Wi-Fi could not be switched on."
            raise WifiError(msg)
        self._radio = RADIO_READY

    def _require_supported(self) -> None:
        if not self._supported:
            msg = "Wi-Fi management is not supported on this host."
            raise WifiError(msg)
