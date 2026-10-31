"""The WifiManager interface: what MLSC needs from the host's Wi-Fi, independent of the tool that provides it."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from mlsc.diagnosis import Diagnosis

CLIENT = "client"
HOTSPOT = "hotspot"

# The states of the Wi-Fi Radio of the chosen Wi-Fi Adapter.
RADIO_READY = "ready"
RADIO_SWITCHED_OFF = "switched_off"
RADIO_BLOCKED = "blocked"
RADIO_UNAVAILABLE = "unavailable"
RADIO_NO_ADAPTER = "no_adapter"


class WifiError(Exception):
    """A Wi-Fi change that could not be made. The message is meant for the user."""


@dataclass(frozen=True)
class Capabilities:
    supported: bool
    hotspot: bool
    country: str | None
    radio: str = RADIO_READY
    interface: str | None = None
    pinned: bool = False


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


def radio_problem(capabilities: Capabilities) -> Diagnosis | None:
    """The warning for a radio that is not ready, with the wording of the switched-off decision. None when it is ready or unsupported."""
    if not capabilities.supported or capabilities.radio == RADIO_READY:
        return None
    interface = capabilities.interface
    if capabilities.radio == RADIO_NO_ADAPTER:
        message = f"The configured Wi-Fi adapter {interface} was not found." if capabilities.pinned else "No Wi-Fi adapter was found."
        return Diagnosis.warning(message, "Plug in a Wi-Fi adapter, or manage the network yourself.")
    if capabilities.radio == RADIO_BLOCKED:
        return Diagnosis.warning("Wi-Fi is blocked by a hardware switch.", "Switch the hardware Wi-Fi switch on.")
    if capabilities.radio == RADIO_SWITCHED_OFF:
        return Diagnosis.warning("Wi-Fi is switched off.", "Turn it on from the Wi-Fi page, or run: sudo nmcli radio wifi on")
    return Diagnosis.warning(f"The Wi-Fi adapter {interface} is not available.", "Check the adapter's driver and firmware (dmesg | grep -i wlan).")


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

    @abstractmethod
    def enable_radio(self) -> None:
        """Switch the Wi-Fi Radio on. Only allowed from `switched_off`; fails with the state's message when it stays unusable."""

    def radio(self) -> str:
        """The state of the Wi-Fi Radio, one of the `RADIO_*` constants. Hosts that can answer cheaply override this."""
        return self.capabilities().radio

    def require_ready(self) -> None:
        """Raise the message of the radio state unless the radio is ready: no change can be made then."""
        problem = radio_problem(self.capabilities())
        if problem is not None:
            raise WifiError(problem.message)

    def hotspot_clients(self) -> int:
        """How many devices are connected to the Hotspot. 0 when it is down. At least 1 when the host cannot tell."""
        return 0

    def diagnose(self) -> Diagnosis:
        capabilities = self.capabilities()
        if not capabilities.supported:
            return Diagnosis.warning("NetworkManager is not available, so MLSC cannot manage Wi-Fi.", "Install NetworkManager or manage Wi-Fi yourself.")
        problem = radio_problem(capabilities)
        if problem is not None:
            return problem
        if not capabilities.hotspot:
            return Diagnosis.warning("The Wi-Fi adapter does not support the Hotspot.", "Use a Wi-Fi adapter that supports the Hotspot.")
        if capabilities.country is None:
            return Diagnosis.warning("The Wi-Fi country is not set, so the radio may be blocked.", "Set it with: sudo raspi-config nonint do_wifi_country <CC>")
        return Diagnosis.ok(f"Wi-Fi is ready (country {capabilities.country}).")
