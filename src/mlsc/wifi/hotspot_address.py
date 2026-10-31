"""The IPv4 address of the Hotspot: NetworkManager's default and the rules for a chosen one. The netmask is fixed at /24."""
from __future__ import annotations

import ipaddress
import re

from mlsc.wifi.manager import WifiError

DEFAULT_HOTSPOT_ADDRESS = "10.42.0.1"
PREFIX_LENGTH = 24
PRIVATE_RANGES = tuple(ipaddress.ip_network(cidr) for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
DOTTED_QUAD = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def hotspot_network(address: str) -> ipaddress.IPv4Network:
    """The /24 the Hotspot serves from `address`."""
    return ipaddress.ip_network(f"{address}/{PREFIX_LENGTH}", strict=False)


def clashing_network(address: str, connected: list[str]) -> str | None:
    """The first of the connected networks (CIDR text such as `192.168.1.20/24`) that overlaps the Hotspot's /24, as its network address."""
    hotspot = hotspot_network(address)
    for text in connected:
        try:
            network = ipaddress.ip_network(text, strict=False)
        except ValueError:
            continue
        if network.version == hotspot.version and network.overlaps(hotspot):
            return str(network)
    return None


def validate_hotspot_address(address: str, connected: list[str]) -> str:
    """Return `address` when the Hotspot can use it, else raise a WifiError with a message for the user."""
    if not DOTTED_QUAD.match(address):
        msg = "The Hotspot address must be an IPv4 address such as 192.168.50.1."
        raise WifiError(msg)
    try:
        ip = ipaddress.IPv4Address(address)
    except ValueError as e:
        msg = "The Hotspot address must be an IPv4 address such as 192.168.50.1."
        raise WifiError(msg) from e
    if not any(ip in private for private in PRIVATE_RANGES):
        msg = "The Hotspot address must be a private address: 10.x.x.x, 172.16.x.x to 172.31.x.x or 192.168.x.x."
        raise WifiError(msg)
    network = hotspot_network(address)
    if ip in {network.network_address, network.broadcast_address}:
        msg = f"{address} is the network or broadcast address of {network}; choose a host address such as {network.network_address + 1}."
        raise WifiError(msg)
    clash = clashing_network(address, connected)
    if clash:
        msg = f"{address} is in {clash}, a network the Pi is connected to. Choose an address in another network."
        raise WifiError(msg)
    return address
