import pytest

from mlsc import host as host_module
from mlsc.host import Host

pytestmark = pytest.mark.unit


def test_pi_model_is_none_when_there_is_no_device_tree(tmp_path):
    assert Host(device_tree_model=tmp_path / "missing").pi_model() is None


def test_pi_model_strips_the_trailing_nul(tmp_path):
    model = tmp_path / "model"
    model.write_bytes(b"Raspberry Pi 4 Model B\x00")

    assert Host(device_tree_model=model).pi_model() == "Raspberry Pi 4 Model B"


AUDIO_CASES = [("dtparam=audio=on\n", True), ("#dtparam=audio=on\n", False), ("dtparam=audio=off\n", False), ("", False)]


@pytest.mark.parametrize(("text", "expected"), AUDIO_CASES)
def test_analog_audio_enabled_reads_the_boot_config(tmp_path, text, expected):
    config = tmp_path / "config.txt"
    config.write_text(text)

    assert Host(boot_configs=[config]).analog_audio_enabled() is expected


def test_analog_audio_last_setting_wins(tmp_path):
    config = tmp_path / "config.txt"
    config.write_text("dtparam=audio=on\ndtparam=audio=off\n")

    assert Host(boot_configs=[config]).analog_audio_enabled() is False


def test_analog_audio_is_found_among_other_dtparams(tmp_path):
    config = tmp_path / "config.txt"
    config.write_text("dtparam=i2s=on,audio=on\n")

    assert Host(boot_configs=[config]).analog_audio_enabled() is True


def test_analog_audio_is_disabled_without_a_boot_config(tmp_path):
    assert Host(boot_configs=[tmp_path / "missing"]).analog_audio_enabled() is False


def test_has_ws281x_checks_the_import_names(monkeypatch):
    monkeypatch.setattr(host_module.importlib.util, "find_spec", lambda name: object() if name == "_rpi_ws281x" else None)

    assert Host().has_ws281x() is True


def test_has_ws281x_is_false_without_either_module(monkeypatch):
    monkeypatch.setattr(host_module.importlib.util, "find_spec", lambda _name: None)

    assert Host().has_ws281x() is False


def test_gpio_memory_is_usable_off_linux(monkeypatch):
    monkeypatch.setattr(host_module.sys, "platform", "win32")

    assert Host().can_use_gpio_memory() is True


def test_gpio_memory_needs_root_or_access_on_linux(monkeypatch):
    monkeypatch.setattr(host_module.sys, "platform", "linux")
    monkeypatch.setattr(host_module.os, "geteuid", lambda: 1000, raising=False)
    monkeypatch.setattr(host_module.os, "access", lambda *_: False)

    assert Host().can_use_gpio_memory() is False


def test_gpio_memory_is_usable_as_root(monkeypatch):
    monkeypatch.setattr(host_module.sys, "platform", "linux")
    monkeypatch.setattr(host_module.os, "geteuid", lambda: 0, raising=False)

    assert Host().can_use_gpio_memory() is True


def test_run_returns_the_exit_code_and_output():
    code, output = Host().run([host_module.sys.executable, "-c", "print('hi')"])

    assert code == 0
    assert output.strip() == "hi"


def test_run_reports_a_missing_command():
    code, output = Host().run(["definitely-not-a-command-mlsc"])

    assert code == 127
    assert "not found" in output
