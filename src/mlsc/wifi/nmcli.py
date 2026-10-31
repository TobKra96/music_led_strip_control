"""WifiManager on top of NetworkManager's `nmcli`, parsed in terse mode (`-t`)."""
from __future__ import annotations

import re
from collections.abc import Callable

from loguru import logger

from mlsc.wifi.manager import CLIENT, HOTSPOT, Capabilities, HotspotInfo, Network, WifiError, WifiManager, WifiStatus

HOTSPOT_CONNECTION = "MLSC-Hotspot"
CONNECT_TIMEOUT_SECONDS = 60
WIFI_TYPE = "802-11-wireless"
UNSET_COUNTRY = "00"
NO_CONNECTION = ("", "--")
NO_SECURITY = ("", "--")
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


class NmcliWifiManager(WifiManager):
    def __init__(self, run: CommandRunner) -> None:
        self._run = run

    def capabilities(self) -> Capabilities:
        device = self._wifi_device()
        if device is None:
            return Capabilities(supported=False, hotspot=False, country=None)
        return Capabilities(supported=True, hotspot=self._supports_access_point(device), country=self._country())

    def status(self) -> WifiStatus:
        device = self._wifi_device()
        if device is None:
            return WifiStatus(CLIENT, connected=False, ssid=None, ip=None, hotspot=None)
        connection, ip = self._active_connection(device)
        if connection == HOTSPOT_CONNECTION:
            return WifiStatus(HOTSPOT, connected=False, ssid=None, ip=ip, hotspot=self._hotspot_info())
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
            raise WifiError(_error_text(output, password))

    def forget(self, ssid: str) -> None:
        self._require_device()
        if ssid not in self._known_ssids():
            msg = f"The network {ssid} is not saved."
            raise WifiError(msg)
        code, output = self._run(["nmcli", "connection", "delete", "id", ssid])
        if code != 0:
            raise WifiError(_error_text(output))

    def start_hotspot(self, ssid: str | None, password: str | None) -> None:
        device = self._require_device()
        if not self._supports_access_point(device):
            msg = "The Wi-Fi adapter does not support the Hotspot."
            raise WifiError(msg)
        command = ["nmcli", "device", "wifi", "hotspot", "ifname", device, "con-name", HOTSPOT_CONNECTION]
        command += ["ssid", ssid] if ssid else []
        command += ["password", password] if password else []
        code, output = self._run(command)
        if code != 0:
            raise WifiError(_error_text(output, password))

    def stop_hotspot(self) -> None:
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
        code, output = self._run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
        if code != 0:
            return None
        rows = (split_terse(line) for line in output.splitlines())
        return next((row[0] for row in rows if row[1:2] == ["wifi"]), None)

    def _require_device(self) -> str:
        device = self._wifi_device()
        if device is None:
            msg = "Wi-Fi management is not supported on this host."
            raise WifiError(msg)
        return device

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

    def _hotspot_info(self) -> HotspotInfo | None:
        command = ["nmcli", "-t", "-s", "-g", "802-11-wireless.ssid,802-11-wireless-security.psk", "connection", "show", HOTSPOT_CONNECTION]
        code, output = self._run(command)
        if code != 0:
            return None
        # `-g` escapes colons and backslashes like `-t` does.
        ssid, _, password = output.partition("\n")
        return HotspotInfo(split_terse(ssid)[0], split_terse(password)[0] or None)

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
