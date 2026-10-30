import pytest

from mlsc.host import Host
from mlsc.output_setup import DEFAULT_VOLTS, estimate_power, max_fps, setup_options, split_suggestion, validate_output

pytestmark = pytest.mark.unit


class PiHost(Host):
    def __init__(self, model="Raspberry Pi 4 Model B Rev 1.5") -> None:
        super().__init__(boot_configs=())
        self.model = model

    def pi_model(self):
        return self.model


def device_config(**overrides):
    config = {
        "led_count": 100, "led_mid": 50, "led_brightness": 100, "output_type": "output_raspi",
        "chip_family": "ws2812", "colour_order": "grb", "white_channel": False,
        "power_limit": {"enabled": True, "supply_amps": 5.0, "ma_per_led": 60, "mode": "warn"},
        "output": {
            "output_raspi": {"led_pin": 18, "led_channel": 0, "led_dma": 10, "led_freq_hz": 800000, "led_invert": False},
            "output_udp": {"udp_client_ip": "192.168.1.5", "udp_client_port": 7777},
        },
    }
    config.update(overrides)
    return config


def fields(errors):
    return {error["field"] for error in errors}


def test_a_valid_config_has_no_errors():
    assert validate_output(device_config(), PiHost()) == []


@pytest.mark.parametrize("pin", [0, 4, 17, 40])
def test_a_pin_the_backend_cannot_drive_is_rejected_with_the_valid_ones(pin):
    config = device_config()
    config["output"]["output_raspi"]["led_pin"] = pin

    errors = validate_output(config, PiHost())

    assert fields(errors) == {"output.output_raspi.led_pin"}
    assert "10, 12, 13, 18, 19, 21" in errors[0]["detail"]


@pytest.mark.parametrize(("key", "value"), [
    ("led_dma", -1), ("led_dma", 15), ("led_freq_hz", 100000), ("led_freq_hz", 2000000),
])
def test_advanced_values_outside_their_range_are_rejected(key, value):
    config = device_config()
    config["output"]["output_raspi"][key] = value

    assert fields(validate_output(config, PiHost())) == {f"output.output_raspi.{key}"}


def test_the_gpio_checks_do_not_apply_to_other_output_types():
    config = device_config(output_type="output_udp")
    config["output"]["output_raspi"]["led_pin"] = 4

    assert validate_output(config, PiHost()) == []


def test_the_pin_is_not_checked_on_a_pi_5_where_no_backend_exists():
    config = device_config()
    config["output"]["output_raspi"]["led_pin"] = 4

    assert validate_output(config, PiHost("Raspberry Pi 5 Model B Rev 1.0")) == []


@pytest.mark.parametrize(("led_count", "led_mid"), [(100, 100), (100, -1), (100, 150)])
def test_the_middle_must_be_a_pixel_of_the_strip(led_count, led_mid):
    assert fields(validate_output(device_config(led_count=led_count, led_mid=led_mid), PiHost())) == {"led_mid"}


def test_a_strip_without_pixels_is_rejected():
    assert "led_count" in fields(validate_output(device_config(led_count=0, led_mid=0), PiHost()))


def test_a_white_channel_needs_an_sk6812():
    assert fields(validate_output(device_config(white_channel=True), PiHost())) == {"white_channel"}
    assert validate_output(device_config(white_channel=True, chip_family="sk6812"), PiHost()) == []


@pytest.mark.parametrize(("pin", "channel"), [(18, 0), (12, 0), (13, 1), (19, 1), (10, 0), (21, 0)])
def test_setup_options_derive_the_channel_from_the_pin(pin, channel):
    assert setup_options(device_config(), PiHost())["pin_channels"][str(pin)] == channel


def test_setup_options_offer_only_valid_pins_for_the_model():
    options = setup_options(device_config(), PiHost())

    assert sorted(map(int, options["pin_channels"])) == [10, 12, 13, 18, 19, 21]
    assert options["pi_model"] == "Raspberry Pi 4 Model B Rev 1.5"
    assert options["experimental"] is None


def test_a_pi_5_has_no_pins_and_an_experimental_notice():
    options = setup_options(device_config(), PiHost("Raspberry Pi 5 Model B Rev 1.0"))

    assert options["pin_channels"] == {}
    assert "experimental" in options["experimental"].lower()


def test_the_estimated_draw_is_the_worst_case_scaled_by_brightness():
    estimate = estimate_power(device_config(led_count=100, led_brightness=50))

    assert estimate["amps"] == pytest.approx(3.0)
    assert estimate["watts"] == pytest.approx(3.0 * DEFAULT_VOLTS)
    assert estimate["warning"] is None


def test_a_draw_above_the_supply_is_a_warning_when_the_limit_is_enabled():
    estimate = estimate_power(device_config(led_count=124))

    assert estimate["amps"] == pytest.approx(7.44)
    assert "7.4 A" in estimate["warning"]
    assert "5.0 A" in estimate["warning"]
    assert "brightness" in estimate["warning"]


def test_a_disabled_limit_never_warns_and_never_dims():
    config = device_config(led_count=124)
    config["power_limit"]["enabled"] = False

    assert estimate_power(config)["warning"] is None


def test_the_supply_voltage_scales_the_watts():
    config = device_config()
    config["power_limit"]["supply_volts"] = 12.0

    assert estimate_power(config)["watts"] == pytest.approx(6.0 * 12.0)


def test_the_expected_max_fps_follows_the_led_count():
    assert max_fps(100) == 256
    assert max_fps(900) == 28
    assert max_fps(0) is None


def test_long_strips_are_suggested_to_be_split():
    assert split_suggestion(300) is None
    assert "split" in split_suggestion(900).lower()
    assert "Device" in split_suggestion(900)
