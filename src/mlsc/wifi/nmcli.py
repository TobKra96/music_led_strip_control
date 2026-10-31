"""WifiManager on top of NetworkManager's `nmcli`, parsed in terse mode (`-t`)."""
from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass

from loguru import logger

from mlsc.wifi.hotspot_address import PREFIX_LENGTH
from mlsc.wifi.manager import (
    CLIENT,
    HOTSPOT,
    RADIO_BLOCKED,
    RADIO_NO_ADAPTER,
    RADIO_READY,
    RADIO_SWITCHED_OFF,
    RADIO_UNAVAILABLE,
    Capabilities,
    HotspotInfo,
    Network,
    WifiError,
    WifiManager,
    WifiStatus,
    radio_problem,
)

HOTSPOT_CONNECTION = "MLSC-Hotspot"
CONNECT_TIMEOUT_SECONDS = 60
WIFI_TYPE = "802-11-wireless"
UNSET_COUNTRY = "00"
NO_CONNECTION = ("", "--")
NO_SECURITY = ("", "--")
MAX_HOTSPOT_PROFILES = 10
RADIO_WAIT_SECONDS = 10
UNUSABLE_STATES = {"unavailable", "unmanaged"}
IP_ADDRESS_LINE = re.compile(r"^\d+:\s+(\S+)\s+inet\s+(\S+)")
COUNTRY_PATTERN = re.compile(r"^country (\w\w):", re.MULTILINE)

# Runs a command line and returns its exit code and combined output; `Host.run` fits.
CommandRunner = Callable[..., tuple[int, str]]


def split_terse(line: str) -> list[str]:
    """Split a line of `nmcli -t` output at the colons that are not escaped, and unescape the fields."""
    fields = [""]
    chars = iter(line)
    for char in chars:
        if char == "\\":
            fields[-1] += next(chars, "\\")
        elif char == ":":
            fields.append("")
        else:
            fields[-1] += char
    return fields


@dataclass(frozen=True)
class _Adapter:
    """The Wi-Fi Adapter MLSC works with, or None when there is none, and the state of its radio."""

    name: str | None
    radio: str
    pinned: bool


class NmcliWifiManager(WifiManager):
    def __init__(self, run: CommandRunner, interface: str | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        """`interface` pins the Wi-Fi Adapter (the `wifi.interface` config key); without it the best usable one is picked."""
        self._run = run
        self._interface = interface or None
        self._sleep = sleep

    def capabilities(self) -> Capabilities:
        adapter = self._adapter()
        if adapter is None:
            return Capabilities(supported=False, hotspot=False, country=None)
        hotspot = adapter.name is not None and self._supports_access_point(adapter.name)
        return Capabilities(True, hotspot, self._country(), adapter.radio, adapter.name or self._interface, adapter.pinned)

    def radio(self) -> str:
        adapter = self._adapter()
        return adapter.radio if adapter else RADIO_READY

    def require_ready(self) -> None:
        self._require_device()

    def enable_radio(self) -> None:
        adapter = self._adapter()
        if adapter is None:
            msg = "Wi-Fi management is not supported on this host."
            raise WifiError(msg)
        if adapter.radio == RADIO_READY:
            return
        if adapter.radio != RADIO_SWITCHED_OFF:
            raise WifiError(self._problem_message(adapter))
        self._run(["rfkill", "unblock", "wifi"])
        code, output = self._run(["nmcli", "radio", "wifi", "on"])
        if code != 0:
            raise WifiError(_error_text(output))
        for _ in range(RADIO_WAIT_SECONDS):
            if self.radio() == RADIO_READY:
                return
            self._sleep(1)
        if self.radio() != RADIO_READY:
            msg = "Wi-Fi was switched on, but the adapter did not come up."
            raise WifiError(msg)

    def status(self) -> WifiStatus:
        device = self._wifi_device()
        if device is None:
            return WifiStatus(CLIENT, connected=False, ssid=None, ip=None, hotspot=None)
        connection, ip = self._active_connection(device)
        if connection == HOTSPOT_CONNECTION:
            return WifiStatus(HOTSPOT, connected=False, ssid=None, ip=ip, hotspot=self._hotspot_info(ip))
        return WifiStatus(CLIENT, connected=connection is not None, ssid=connection, ip=ip, hotspot=None)

    def scan(self) -> list[Network]:
        if self._wifi_device() is None:
            return []
        code, output = self._run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes"])
        if code != 0:
            logger.warning("Scanning for Wi-Fi networks failed: {}", output)
            return []
        known = self._known_ssids()
        networks: dict[str, Network] = {}
        for line in output.splitlines():
            in_use, ssid, signal, security = [*split_terse(line), "", "", "", ""][:4]
            if not ssid:
                continue
            network = Network(ssid, int(signal) if signal.isdigit() else 0, None if security in NO_SECURITY else security, in_use.strip() == "*", ssid in known)
            # One entry per SSID: several access points share it, the connected or strongest one wins.
            best = networks.get(ssid)
            if best is None or (network.in_use, network.signal) > (best.in_use, best.signal):
                networks[ssid] = network
        return list(networks.values())

    def connect(self, ssid: str, password: str | None) -> None:
        device = self._require_device()
        was_known = ssid in self._known_ssids()
        command = ["nmcli", "device", "wifi", "connect", ssid, *(["password", password] if password else []), "ifname", device]
        code, output = self._run(command, timeout=CONNECT_TIMEOUT_SECONDS)
        if code != 0:
            if not was_known:
                # nmcli keeps the profile of a failed first connection, which would then retry with the wrong password.
                self._run(["nmcli", "connection", "delete", "id", ssid])
            raise WifiError(_connect_error(ssid, output, password))

    def forget(self, ssid: str) -> None:
        self._require_device()
        if ssid not in self._known_ssids():
            msg = f"The network {ssid} is not saved."
            raise WifiError(msg)
        code, output = self._run(["nmcli", "connection", "delete", "id", ssid])
        if code != 0:
            raise WifiError(_error_text(output))

    def start_hotspot(self, ssid: str | None, password: str | None, address: str | None = None) -> None:
        device = self._require_device()
        if not self._supports_access_point(device):
            msg = "The Wi-Fi adapter does not support the Hotspot."
            raise WifiError(msg)
        self._delete_hotspot_profiles()
        command = ["nmcli", "device", "wifi", "hotspot", "ifname", device, "con-name", HOTSPOT_CONNECTION]
        command += ["ssid", ssid] if ssid else []
        command += ["password", password] if password else []
        code, output = self._run(command)
        if code != 0:
            raise WifiError(_error_text(output, password))
        if address:
            self._set_hotspot_address(address)

    def _set_hotspot_address(self, address: str) -> None:
        """`nmcli device wifi hotspot` always starts on the default address: change the profile, then bring it up again (still `shared`: DHCP, DNS and NAT)."""
        modify = ["nmcli", "connection", "modify", HOTSPOT_CONNECTION, "ipv4.addresses", f"{address}/{PREFIX_LENGTH}", "ipv4.method", "shared"]
        for command in (modify, ["nmcli", "connection", "up", "id", HOTSPOT_CONNECTION]):
            code, output = self._run(command)
            if code != 0:
                raise WifiError(_error_text(output))

    def connected_networks(self) -> list[str]:
        code, output = self._run(["ip", "-4", "-o", "addr", "show"])
        if code != 0:
            return []
        device = self._wifi_device()
        hotspot_device = device if device and self._active_connection(device)[0] == HOTSPOT_CONNECTION else None
        networks = []
        for line in output.splitlines():
            match = IP_ADDRESS_LINE.match(line)
            if match and match[1] != "lo" and match[1] != hotspot_device:
                networks.append(match[2])
        return networks

    def stop_hotspot(self) -> None:
        self._delete_hotspot_profiles()

    def _delete_hotspot_profiles(self) -> None:
        """Delete every profile named like the Hotspot: `nmcli device wifi hotspot` adds a new one on each start."""
        for _ in range(MAX_HOTSPOT_PROFILES):
            if HOTSPOT_CONNECTION not in self._connection_names():
                return
            code, output = self._run(["nmcli", "connection", "delete", "id", HOTSPOT_CONNECTION])
            if code != 0:
                raise WifiError(_error_text(output))

    def hotspot_clients(self) -> int:
        device = self._wifi_device()
        if device is None:
            return 0
        code, output = self._run(["iw", "dev", device, "station", "dump"])
        if code != 0:
            # Unknown counts as "someone is connected": the retry would otherwise cut off a phone that is setting the Pi up.
            return 1
        return len(re.findall(r"^Station ", output, re.MULTILINE))

    def _wifi_device(self) -> str | None:
        adapter = self._adapter()
        return adapter.name if adapter else None

    def _adapter(self) -> _Adapter | None:
        """Pick the Wi-Fi Adapter. None when NetworkManager does not answer."""
        code, output = self._run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
        if code != 0:
            return None
        rows = sorted(row for row in (split_terse(line) for line in output.splitlines()) if row[1:2] == ["wifi"])
        adapters = {row[0]: (row[2:3] or [""])[0] for row in rows}
        if self._interface:
            chosen = self._interface if self._interface in adapters else None
        else:
            chosen = self._best(adapters)
        if chosen is None:
            return _Adapter(None, RADIO_NO_ADAPTER, pinned=self._interface is not None)
        return _Adapter(chosen, self._radio_state(adapters[chosen]), pinned=self._interface is not None)

    def _best(self, adapters: dict[str, str]) -> str | None:
        """The usable adapter holding the connection, else one with Hotspot support, else the first; with none usable, the first."""
        usable = [name for name, state in adapters.items() if state not in UNUSABLE_STATES]
        if len(usable) > 1:
            usable.sort(key=lambda name: (adapters[name] != "connected", not self._supports_access_point(name)))
        return (usable or list(adapters))[0] if adapters else None

    def _radio_state(self, adapter_state: str) -> str:
        code, output = self._run(["nmcli", "-t", "-f", "WIFI-HW,WIFI", "radio"])
        hardware, software = [*split_terse(output.strip()), "enabled", "enabled"][:2] if code == 0 else ("enabled", "enabled")
        if hardware == "disabled":
            return RADIO_BLOCKED
        if software == "disabled":
            return RADIO_SWITCHED_OFF
        return RADIO_UNAVAILABLE if adapter_state == "unavailable" else RADIO_READY

    def _problem_message(self, adapter: _Adapter) -> str:
        capabilities = Capabilities(True, False, None, adapter.radio, adapter.name or self._interface, adapter.pinned)
        problem = radio_problem(capabilities)
        return problem.message if problem else ""

    def _require_device(self) -> str:
        adapter = self._adapter()
        if adapter is None:
            msg = "Wi-Fi management is not supported on this host."
            raise WifiError(msg)
        if adapter.name is None or adapter.radio != RADIO_READY:
            raise WifiError(self._problem_message(adapter))
        return adapter.name

    def _supports_access_point(self, device: str) -> bool:
        code, output = self._run(["nmcli", "-t", "-g", "WIFI-PROPERTIES.AP", "device", "show", device])
        return code == 0 and output.strip() == "yes"

    def _country(self) -> str | None:
        code, output = self._run(["iw", "reg", "get"])
        if code != 0:
            return None
        return next((country for country in COUNTRY_PATTERN.findall(output) if country != UNSET_COUNTRY), None)

    def _active_connection(self, device: str) -> tuple[str | None, str | None]:
        code, output = self._run(["nmcli", "-t", "-f", "GENERAL.CONNECTION,IP4.ADDRESS", "device", "show", device])
        if code != 0:
            return None, None
        connection = ip = None
        for line in output.splitlines():
            key, _, value = line.partition(":")
            value = split_terse(value)[0]
            if key == "GENERAL.CONNECTION" and value not in NO_CONNECTION:
                connection = value
            elif key.startswith("IP4.ADDRESS") and value:
                ip = value.split("/")[0]
        return connection, ip

    def _hotspot_info(self, address: str | None) -> HotspotInfo | None:
        command = ["nmcli", "-t", "-s", "-g", "802-11-wireless.ssid,802-11-wireless-security.psk", "connection", "show", HOTSPOT_CONNECTION]
        code, output = self._run(command)
        if code != 0:
            return None
        # `-g` escapes colons and backslashes like `-t` does.
        # Profiles that an earlier version left behind with the same name add their own lines: the first one is read.
        ssid, password, *_ = [*output.split("\n"), "", ""]
        return HotspotInfo(split_terse(ssid)[0], split_terse(password)[0] or None, address)

    def _connection_names(self, *, wifi_only: bool = False) -> set[str]:
        code, output = self._run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
        if code != 0:
            return set()
        rows = [split_terse(line) for line in output.splitlines()]
        return {row[0] for row in rows if not wifi_only or row[1:2] == [WIFI_TYPE]}

    def _known_ssids(self) -> set[str]:
        return self._connection_names(wifi_only=True) - {HOTSPOT_CONNECTION}


def _error_text(output: str, secret: str | None = None) -> str:
    text = output.strip().removeprefix("Error:").strip() or "nmcli failed."
    return text.replace(secret, "***") if secret else text


def _connect_error(ssid: str, output: str, password: str | None) -> str:
    """The text for a failed connect. A missing or wrong password gets a plain sentence instead of nmcli's `--ask` hint."""
    if "Secrets were required" in output:
        return f"The password for {ssid} is missing or wrong. Enter it and try again."
    return _error_text(output, password)
