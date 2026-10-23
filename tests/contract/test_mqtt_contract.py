"""Contract for the MQTT client protocol and the ``output_mqtt`` / ``output_udp`` config keys.

The server has no MQTT publisher; the contract is the config keys, the template defaults, and the
payload layout the shipped ESP client parses: one message on ``mqtt_path`` holding RGB bytes per pixel.
"""
import json
from importlib import resources
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from mlsc.webserver.schemas.config_validator_service import ConfigValidatorService

pytestmark = pytest.mark.contract

TEMPLATE = json.loads((resources.files("mlsc") / "config_template.json").read_text())
CLIENT_DIR = Path(__file__).parents[2] / "client"
MQTT_CLIENT = (CLIENT_DIR / "mqtt" / "esp" / "nodemcu_client" / "nodemcu_client.ino").read_text()
UDP_CLIENT = (CLIENT_DIR / "udp" / "esp" / "nodemcu_client" / "nodemcu_client.ino").read_text()


def find_output_section(node):
    if isinstance(node, dict):
        if "output_mqtt" in node and "output_udp" in node:
            return node
        node = list(node.values())
    if isinstance(node, list):
        for value in node:
            found = find_output_section(value)
            if found:
                return found
    return None


def find_property_schema(node, key):
    if isinstance(node, dict):
        if key in node.get("properties", {}):
            return node["properties"][key]
        node = list(node.values())
    if isinstance(node, list):
        for value in node:
            found = find_property_schema(value, key)
            if found:
                return found
    return None


@pytest.fixture
def output_section():
    section = find_output_section(TEMPLATE)
    assert section is not None
    return section


@pytest.fixture
def mqtt_validator():
    return Draft7Validator(find_property_schema(ConfigValidatorService._get_schema(), "output_mqtt"))


def test_template_pins_mqtt_and_udp_config_keys(output_section):
    assert output_section["output_mqtt"] == {"mqtt_broker": "localhost", "mqtt_path": "led/device_a"}
    assert output_section["output_udp"] == {"udp_client_ip": "127.0.0.1", "udp_client_port": 7777}


def test_template_topic_matches_the_esp_client_subscription(output_section):
    topic = output_section["output_mqtt"]["mqtt_path"]

    assert f'client.subscribe("{topic}")' in MQTT_CLIENT


def test_esp_mqtt_client_parses_three_bytes_per_pixel():
    assert "i+=3" in MQTT_CLIENT
    assert "RgbColor pixel((uint8_t)payload[i], (uint8_t)payload[i+1], (uint8_t)payload[i+2])" in MQTT_CLIENT


def test_esp_udp_client_parses_three_bytes_per_pixel():
    assert "RgbColor pixel((uint8_t)packetBuffer[i], (uint8_t)packetBuffer[i+1], (uint8_t)packetBuffer[i+2])" in UDP_CLIENT


def test_validator_accepts_the_template_mqtt_section(mqtt_validator, output_section):
    assert not list(mqtt_validator.iter_errors(output_section["output_mqtt"]))


@pytest.mark.parametrize(
    "bad",
    [
        {"mqtt_broker": "", "mqtt_path": "led/device_a"},
        {"mqtt_broker": "localhost", "mqtt_path": ""},
        {"mqtt_broker": 5, "mqtt_path": "led/device_a"},
        {"mqtt_broker": "localhost"},
        {"mqtt_broker": "localhost", "mqtt_path": "led/device_a", "extra": 1},
    ],
)
def test_validator_rejects_bad_mqtt_sections(mqtt_validator, bad):
    assert list(mqtt_validator.iter_errors(bad))
