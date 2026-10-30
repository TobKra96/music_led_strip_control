import json

import pytest

from mlsc import cli, config_migration, doctor, paths
from mlsc.audio_device import AudioDevice
from mlsc.diagnosis import Diagnosis, Status
from mlsc.host import Host

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("clean_config_env")]


class QuietHost(Host):
    def __init__(self, nmcli=True, nmcli_state=(0, "connected"), ws281x=True) -> None:
        self.nmcli = nmcli
        self.nmcli_state = nmcli_state
        self.ws281x = ws281x
        self.model = None
        self.gpio_memory = True
        self.analog_audio = False

    def has_ws281x(self):
        return self.ws281x

    def pi_model(self):
        return self.model

    def can_use_gpio_memory(self):
        return self.gpio_memory

    def analog_audio_enabled(self):
        return self.analog_audio

    def which(self, command):
        return f"/usr/bin/{command}" if self.nmcli else None

    def run(self, command):  # ruff: ignore[unused-method-argument]
        return self.nmcli_state


class FakeCapture:
    def __init__(self, devices=None, error=None) -> None:
        self.devices = devices if devices is not None else [AudioDevice(0, "Mic", 44100)]
        self.error = error

    def list_devices(self):
        if self.error:
            raise self.error
        return self.devices


def write_config(config_dir, audio=None, **device_overrides):
    config = config_migration.load_template()
    device = {**config["default_device"], "output_type": "output_udp", **device_overrides}
    config["device_configs"] = {"device_0": device}
    config["audio"] = {**config["audio"], **(audio or {})}
    (config_dir / "config.json").write_text(json.dumps(config))


def checks_by_name(config_dir, **kwargs):
    kwargs.setdefault("host", QuietHost())
    kwargs.setdefault("capture_factory", FakeCapture)
    return {check.name: check.diagnosis for check in doctor.run_checks(config_dir, **kwargs)}


def test_everything_healthy(config_dir):
    write_config(config_dir)

    results = checks_by_name(config_dir)

    assert {name: d.status for name, d in results.items()} == {
        "config": Status.OK,
        "output device_0": Status.OK,
        "audio": Status.OK,
        "wifi": Status.OK,
        "permissions": Status.OK,
    }


def test_missing_config_is_a_warning(config_dir):
    result = checks_by_name(config_dir)["config"]

    assert result.status is Status.WARNING
    assert "defaults" in result.message


def test_invalid_json_is_an_error_that_points_to_reset(config_dir):
    (config_dir / "config.json").write_text("{nope")

    result = checks_by_name(config_dir)["config"]

    assert result.status is Status.ERROR
    assert "mlsc config reset" in result.suggested_fix


def test_old_config_version_points_to_migrate(config_dir):
    (config_dir / "config.json").write_text(json.dumps({"version": 3}))

    result = checks_by_name(config_dir)["config"]

    assert result.status is Status.ERROR
    assert "mlsc config migrate" in result.suggested_fix


def test_config_failing_the_schema_is_an_error(config_dir):
    write_config(config_dir, led_count="many")

    result = checks_by_name(config_dir)["config"]

    assert result.status is Status.ERROR
    assert "led_count" in result.message


def test_unsupported_output_type_is_an_error(config_dir):
    write_config(config_dir, output_type="output_mqtt")

    result = checks_by_name(config_dir)["output device_0"]

    assert result.status is Status.ERROR
    assert "output_mqtt" in result.message


def test_output_diagnosis_is_reported_per_device(config_dir):
    write_config(config_dir, output_type="output_raspi")

    result = checks_by_name(config_dir, host=QuietHost(ws281x=False))["output device_0"]

    assert result.status is Status.ERROR
    assert "rpi_ws281x" in result.message


def test_no_audio_devices_is_an_error(config_dir):
    write_config(config_dir)

    result = checks_by_name(config_dir, capture_factory=lambda: FakeCapture(devices=[]))["audio"]

    assert result.status is Status.ERROR
    assert result.suggested_fix


def test_audio_backend_failure_is_an_error(config_dir):
    write_config(config_dir)

    def broken():
        msg = "no portaudio"
        raise RuntimeError(msg)

    result = checks_by_name(config_dir, capture_factory=broken)["audio"]

    assert result.status is Status.ERROR
    assert "no portaudio" in result.message


def test_listing_failure_is_an_error(config_dir):
    write_config(config_dir)

    result = checks_by_name(config_dir, capture_factory=lambda: FakeCapture(error=OSError("denied")))["audio"]

    assert result.status is Status.ERROR


def test_browser_source_needs_no_server_device(config_dir):
    write_config(config_dir, audio={"source": "browser"})

    result = checks_by_name(config_dir, capture_factory=lambda: FakeCapture(devices=[]))["audio"]

    assert result.status is Status.OK
    assert "browser" in result.message.lower()


def test_wifi_without_networkmanager_is_a_warning(config_dir, monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")

    result = checks_by_name(config_dir, host=QuietHost(nmcli=False))["wifi"]

    assert result.status is Status.WARNING
    assert "NetworkManager" in result.message


def test_wifi_disconnected_is_a_warning(config_dir, monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")

    result = checks_by_name(config_dir, host=QuietHost(nmcli_state=(0, "disconnected")))["wifi"]

    assert result.status is Status.WARNING


def test_wifi_command_failure_is_a_warning(config_dir, monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")

    result = checks_by_name(config_dir, host=QuietHost(nmcli_state=(8, "NetworkManager is not running")))["wifi"]

    assert result.status is Status.WARNING


def test_wifi_is_skipped_off_linux(config_dir, monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "win32")

    assert checks_by_name(config_dir)["wifi"].status is Status.OK


def test_unwritable_config_dir_is_an_error(config_dir, monkeypatch):
    monkeypatch.setattr(doctor, "_unwritable_reason", lambda _path: "denied")

    result = checks_by_name(config_dir)["permissions"]

    assert result.status is Status.ERROR
    assert "denied" in result.message


def test_writable_probe_checks_a_missing_directory_without_creating_it(tmp_path):
    target = tmp_path / "new" / "dir"

    assert doctor._unwritable_reason(target) is None  # ruff: ignore[private-member-access]
    assert not target.exists()


def test_writable_probe_reports_a_missing_directory_under_a_read_only_parent(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor.os, "access", lambda *_: False)

    assert "no write permission" in doctor._unwritable_reason(tmp_path / "new")  # ruff: ignore[private-member-access]


def test_wifi_connected_without_internet_is_fine(config_dir, monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")

    assert checks_by_name(config_dir, host=QuietHost(nmcli_state=(0, "connected (local only)")))["wifi"].status is Status.OK


def test_incomplete_output_settings_are_an_error_not_a_crash(config_dir, monkeypatch):
    write_config(config_dir)

    def missing_key(_device_config, _host):
        message = "udp_client_ip"
        raise KeyError(message)

    monkeypatch.setattr(doctor.OUTPUTS["output_udp"], "diagnose", missing_key)

    results = checks_by_name(config_dir)

    assert results["output device_0"].status is Status.ERROR
    assert "audio" in results


def test_writable_probe_reports_a_file_in_the_way(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")

    assert doctor._unwritable_reason(blocker / "sub") is not None  # ruff: ignore[private-member-access]


def test_report_marks_each_check_and_prints_the_fix():
    checks = [doctor.Check("a", Diagnosis.ok("fine")), doctor.Check("b", Diagnosis.error("bad", "do this"))]

    text = doctor.format_report(checks)

    assert "[OK] a: fine" in text
    assert "[ERROR] b: bad" in text
    assert "Fix: do this" in text


def test_doctor_command_exits_nonzero_on_an_error(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "run_checks", lambda _dir, **_kw: [doctor.Check("x", Diagnosis.error("bad"))])

    assert cli.main(["doctor"]) == 1
    assert "[ERROR] x: bad" in capsys.readouterr().out


def test_doctor_command_exits_zero_on_warnings(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "run_checks", lambda _dir, **_kw: [doctor.Check("x", Diagnosis.warning("hm"))])

    assert cli.main(["doctor"]) == 0
    assert "[WARNING] x: hm" in capsys.readouterr().out


def test_doctor_uses_the_config_dir(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(doctor, "run_checks", lambda config_dir, **_kw: seen.append(config_dir) or [])

    cli.main(["--config-dir", str(tmp_path), "doctor"])

    assert seen == [paths.config_dir()]
