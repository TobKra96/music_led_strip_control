"""Choose the WifiManager for this host."""
from __future__ import annotations

import os
import sys

from mlsc.host import Host
from mlsc.wifi.manager import WifiManager
from mlsc.wifi.mock import MockNetwork, MockWifiManager
from mlsc.wifi.nmcli import NmcliWifiManager

BACKEND_ENV_VAR = "MLSC_WIFI_BACKEND"
DEMO_NETWORKS = (MockNetwork("Home", 80, "WPA2", "password"), MockNetwork("Guest", 55, None), MockNetwork("Neighbour", 30, "WPA2", "password"))


def create_wifi_manager(backend: str | None = None, host: Host | None = None, platform: str = sys.platform) -> WifiManager:
    """`nmcli` where NetworkManager is installed, otherwise a manager that reports Wi-Fi as unsupported.

    `mock` (or `MLSC_WIFI_BACKEND=mock`) selects a Mock with demo networks, for developing the UI without a radio.
    """
    backend = backend or os.environ.get(BACKEND_ENV_VAR, "auto")
    host = host or Host()
    if backend == "mock":
        return MockWifiManager(networks=DEMO_NETWORKS)
    if platform == "linux" and host.which("nmcli") is not None:
        return NmcliWifiManager(host.run)
    return MockWifiManager(supported=False)
