import pytest

from mlsc.wifi.hotspot_address import DEFAULT_HOTSPOT_ADDRESS, clashing_network, validate_hotspot_address
from mlsc.wifi.manager import WifiError

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("address", ["10.1.2.3", "172.16.0.1", "172.31.255.1", "192.168.50.1", "10.42.0.1"])
def test_a_private_address_is_accepted(address):
    assert validate_hotspot_address(address, []) == address


@pytest.mark.parametrize("address", ["8.8.8.8", "172.32.0.1", "172.15.0.1", "192.169.0.1", "11.0.0.1", "127.0.0.1"])
def test_a_public_address_is_rejected(address):
    with pytest.raises(WifiError, match="private"):
        validate_hotspot_address(address, [])


@pytest.mark.parametrize("address", ["not-an-ip", "192.168.1", "192.168.1.1/24", "::1", "fd00::1", "192.168.1.300"])
def test_text_that_is_not_an_ipv4_address_is_rejected(address):
    with pytest.raises(WifiError, match="IPv4"):
        validate_hotspot_address(address, [])


@pytest.mark.parametrize("address", ["192.168.50.0", "192.168.50.255"])
def test_the_network_and_broadcast_addresses_are_rejected(address):
    with pytest.raises(WifiError, match="network or broadcast"):
        validate_hotspot_address(address, [])


def test_a_subnet_that_overlaps_a_connected_network_is_rejected_by_name():
    with pytest.raises(WifiError, match=r"192\.168\.1\.0/24"):
        validate_hotspot_address("192.168.1.1", ["192.168.1.20/24"])


def test_a_wider_connected_network_overlaps_too():
    with pytest.raises(WifiError, match=r"10\.0\.0\.0/16"):
        validate_hotspot_address("10.0.5.1", ["10.0.0.7/16"])


def test_a_different_subnet_does_not_overlap():
    assert validate_hotspot_address("192.168.2.1", ["192.168.1.20/24"]) == "192.168.2.1"


def test_an_unparsable_connected_network_is_ignored():
    assert clashing_network("192.168.1.1", ["garbage", "192.168.1.20/24"]) == "192.168.1.0/24"
    assert clashing_network("192.168.2.1", ["garbage"]) is None


def test_the_default_is_the_networkmanager_address():
    assert DEFAULT_HOTSPOT_ADDRESS == "10.42.0.1"
