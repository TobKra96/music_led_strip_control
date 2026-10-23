import copy
import json
import threading
from pathlib import Path

import pytest

from mlsc import cli, config_migration
from mlsc.audio_capture.fake import FakeCapture
from mlsc.config_migration import ConfigMigrationError
from mlsc.config_service import ConfigService

pytestmark = pytest.mark.unit

GOLDEN = Path(__file__).parent / "golden"


def no_audio():
    return []


def v2_text():
    return (GOLDEN / "config_v2_real.json").read_text(encoding="utf-8")


def current_config():
    return config_migration.load_template()


@pytest.fixture
def legacy(tmp_path):
    path = tmp_path / "legacy" / ".mlsc" / "config.json"
    path.parent.mkdir(parents=True)
    path.write_text(v2_text(), encoding="utf-8")
    return path


@pytest.fixture
def target_dir(tmp_path):
    return tmp_path / "config"


def test_migrate_data_returns_a_valid_current_config_for_real_old_configs():
    for name in ("config_v1_real.json", "config_v2_real.json"):
        config, report = config_migration.migrate_data(json.loads((GOLDEN / name).read_text(encoding="utf-8")), [])

        assert config["version"] == config_migration.CURRENT_VERSION
        assert report.to_version == config_migration.CURRENT_VERSION


def test_migrate_data_does_not_modify_its_input():
    data = json.loads(v2_text())
    before = copy.deepcopy(data)

    config_migration.migrate_data(data, [])

    assert data == before


def test_migrate_data_preserves_unknown_keys():
    data = json.loads(v2_text())
    data["my_plugin"] = {"x": 1}
    data["general_settings"]["custom"] = True

    config, _ = config_migration.migrate_data(data, [])

    assert config["my_plugin"] == {"x": 1}
    assert config["general_settings"]["custom"] is True


def test_migrate_data_accepts_a_3x_export():
    config, report = config_migration.migrate_data(current_config(), [])

    assert config == current_config()
    assert report.entries == []


def test_migrate_data_refuses_a_newer_version():
    data = current_config()
    data["version"] = 99

    with pytest.raises(ConfigMigrationError, match="version 99"):
        config_migration.migrate_data(data)


def test_migrate_data_refuses_an_invalid_config():
    data = json.loads(v2_text())
    data["general_settings"]["webserver_port"] = "not a port"

    with pytest.raises(ConfigMigrationError, match="not valid"):
        config_migration.migrate_data(data, [])


@pytest.mark.parametrize("version", ["4", True, None])
def test_migrate_data_refuses_a_non_integer_version(version):
    data = current_config()
    data["version"] = version

    with pytest.raises(ConfigMigrationError, match="invalid version"):
        config_migration.migrate_data(data)


def test_migrate_file_copy_migrates_and_never_touches_the_original(legacy, target_dir):
    original = legacy.read_bytes()

    result = config_migration.migrate_file(legacy, target_dir, audio_devices=[])

    assert legacy.read_bytes() == original
    assert result.written
    assert json.loads((target_dir / "config.json").read_text())["version"] == 4
    assert (target_dir / "config.v2.bak.json").read_bytes() == original
    assert json.loads((target_dir / "migration-report.json").read_text())["to_version"] == 4
    assert (target_dir / "config_backup.json").read_bytes() == (target_dir / "config.json").read_bytes()
    assert not list(target_dir.glob("*.tmp"))


def test_migrate_file_dry_run_writes_nothing(legacy, target_dir):
    result = config_migration.migrate_file(legacy, target_dir, dry_run=True, audio_devices=[])

    assert not result.written
    assert result.config["version"] == 4
    assert not target_dir.exists()


def test_migrate_file_never_overwrites_the_version_backup(legacy, target_dir):
    target_dir.mkdir()
    (target_dir / "config.v2.bak.json").write_text("first original")

    config_migration.migrate_file(legacy, target_dir, audio_devices=[])

    assert (target_dir / "config.v2.bak.json").read_text() == "first original"


def test_failed_migration_leaves_everything_untouched(target_dir):
    target_dir.mkdir()
    broken = json.loads(v2_text())
    broken["general_settings"]["webserver_port"] = "bad"
    (target_dir / "config.json").write_text(json.dumps(broken))
    before = (target_dir / "config.json").read_bytes()

    with pytest.raises(ConfigMigrationError) as exc:
        config_migration.prepare_config(target_dir, audio_devices=no_audio)

    assert (target_dir / "config.json").read_bytes() == before
    assert sorted(p.name for p in target_dir.iterdir()) == ["config.json"]
    for hint in ("untouched", "mlsc config reset", "mlsc doctor"):
        assert hint in str(exc.value)


def test_unreadable_source_is_a_migration_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")

    with pytest.raises(ConfigMigrationError, match="not valid JSON"):
        config_migration.migrate_file(bad, tmp_path / "out")


def test_non_object_source_is_a_migration_error(tmp_path):
    bad = tmp_path / "list.json"
    bad.write_text("[]")

    with pytest.raises(ConfigMigrationError, match="config object"):
        config_migration.migrate_file(bad, tmp_path / "out")


def test_prepare_config_migrates_an_old_config_in_place(target_dir):
    target_dir.mkdir()
    (target_dir / "config.json").write_text(v2_text())

    result = config_migration.prepare_config(target_dir, audio_devices=no_audio)

    assert result.report.from_version == 2
    assert json.loads((target_dir / "config.json").read_text())["version"] == 4
    assert (target_dir / "config.v2.bak.json").read_text() == v2_text()


def test_prepare_config_leaves_a_current_config_alone_without_touching_audio(target_dir):
    target_dir.mkdir()
    (target_dir / "config.json").write_text(json.dumps(current_config()))

    def explode():
        message = "audio queried"
        raise AssertionError(message)

    assert config_migration.prepare_config(target_dir, audio_devices=explode) is None
    assert [p.name for p in target_dir.iterdir()] == ["config.json"]


def test_prepare_config_refuses_a_newer_config_unchanged(target_dir):
    target_dir.mkdir()
    newer = json.dumps({**current_config(), "version": 5})
    (target_dir / "config.json").write_text(newer)

    with pytest.raises(ConfigMigrationError, match="version 5"):
        config_migration.prepare_config(target_dir, audio_devices=no_audio)

    assert (target_dir / "config.json").read_text() == newer


def test_prepare_config_leaves_a_corrupt_config_for_the_runtime_fallback(target_dir):
    target_dir.mkdir()
    (target_dir / "config.json").write_text("{corrupt")

    assert config_migration.prepare_config(target_dir, audio_devices=no_audio) is None
    assert (target_dir / "config.json").read_text() == "{corrupt"


def test_prepare_config_copy_migrates_a_legacy_config_from_cwd(legacy, target_dir, monkeypatch):
    monkeypatch.chdir(legacy.parent.parent)

    result = config_migration.prepare_config(target_dir, audio_devices=no_audio)

    assert result.source.samefile(legacy)
    assert legacy.read_text() == v2_text()
    assert (target_dir / "config.json").exists()


def test_prepare_config_creates_the_template_without_any_legacy_config(target_dir, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert config_migration.prepare_config(target_dir, audio_devices=no_audio) is None
    assert json.loads((target_dir / "config.json").read_text()) == current_config()


def test_find_legacy_config_accepts_a_file_or_a_directory(legacy):
    assert config_migration.find_legacy_config(legacy) == legacy
    assert config_migration.find_legacy_config(legacy.parent) == legacy


def test_find_legacy_config_rejects_a_missing_path(tmp_path):
    with pytest.raises(ConfigMigrationError, match="No config found"):
        config_migration.find_legacy_config(tmp_path / "nope")


def test_find_legacy_config_returns_none_when_nothing_exists(tmp_path):
    assert config_migration.find_legacy_config(cwd=tmp_path) is None


def test_reset_config_keeps_the_replaced_config(target_dir):
    target_dir.mkdir()
    (target_dir / "config.json").write_text('{"mine": 1}')

    kept = config_migration.reset_config(target_dir)

    assert kept.read_text() == '{"mine": 1}'
    assert json.loads((target_dir / "config.json").read_text()) == current_config()


def test_list_audio_devices_never_raises(monkeypatch):
    monkeypatch.setattr("mlsc.audio_capture.create_capture", lambda: (_ for _ in ()).throw(OSError("no audio")))

    assert config_migration.list_audio_devices() is None


def test_list_audio_devices_maps_input_devices(monkeypatch):
    monkeypatch.setattr("mlsc.audio_capture.create_capture", lambda: FakeCapture())

    assert config_migration.list_audio_devices() == [
        {"index": 0, "name": "Fake Mic", "host_api": None},
        {"index": 1, "name": "Fake Monitor", "host_api": None},
    ]


def test_config_service_migrates_an_old_config_at_startup(config_dir, monkeypatch):
    monkeypatch.setattr(config_migration, "list_audio_devices", no_audio)
    (config_dir / "config.json").write_text(v2_text())

    service = ConfigService(threading.Lock())

    assert service.config["version"] == 4
    assert (config_dir / "config.v2.bak.json").exists()


def test_config_service_refuses_to_start_on_a_failed_migration(config_dir):
    (config_dir / "config.json").write_text(json.dumps({"version": 99}))

    with pytest.raises(ConfigMigrationError):
        ConfigService(threading.Lock())


def test_config_service_falls_back_to_the_backup_for_a_corrupt_config(config_dir):
    (config_dir / "config.json").write_text(json.dumps(current_config()))
    (config_dir / "config_backup.json").write_text(json.dumps({"version": 4, "from": "backup"}))
    service = ConfigService(threading.Lock())
    (config_dir / "config.json").write_text("{corrupt")

    service.load_config()

    assert service.config["from"] == "backup"
    assert "last-good backup" in service.fallback_warning


def test_cli_config_migrate_dry_run_then_real(legacy, config_dir, capsys, monkeypatch):
    monkeypatch.setattr(config_migration, "list_audio_devices", no_audio)

    assert cli.main(["config", "migrate", "--from", str(legacy), "--dry-run"]) == 0
    assert "Dry run" in capsys.readouterr().out
    assert not (config_dir / "config.json").exists()

    assert cli.main(["config", "migrate", "--from", str(legacy)]) == 0
    assert json.loads((config_dir / "config.json").read_text())["version"] == 4
    assert legacy.read_text() == v2_text()


def test_cli_config_migrate_reports_failure_and_changes_nothing(config_dir, tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")

    assert cli.main(["config", "migrate", "--from", str(bad)]) == 1

    assert "Nothing was changed" in capsys.readouterr().err
    assert not (config_dir / "config.json").exists()


@pytest.mark.usefixtures("config_dir")
def test_cli_config_migrate_without_any_config(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert cli.main(["config", "migrate"]) == 1
    assert "no config found" in capsys.readouterr().err


def test_cli_config_migrate_in_place(config_dir, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_migration, "list_audio_devices", no_audio)
    (config_dir / "config.json").write_text(v2_text())

    assert cli.main(["config", "migrate"]) == 0
    assert json.loads((config_dir / "config.json").read_text())["version"] == 4


def test_cli_config_reset(config_dir):
    (config_dir / "config.json").write_text('{"mine": 1}')

    assert cli.main(["config", "reset"]) == 0
    assert json.loads((config_dir / "config.json").read_text()) == current_config()
    assert (config_dir / "config.pre-reset.bak.json").exists()


def test_migrate_file_refuses_to_replace_an_existing_config_from_another_source(legacy, target_dir):
    target_dir.mkdir()
    (target_dir / "config.json").write_text("mine")

    with pytest.raises(ConfigMigrationError, match="already exists"):
        config_migration.migrate_file(legacy, target_dir, audio_devices=[])

    assert (target_dir / "config.json").read_text() == "mine"
    assert sorted(p.name for p in target_dir.iterdir()) == ["config.json"]


def test_cli_config_migrate_prefers_the_current_config_over_a_legacy_one(legacy, config_dir, monkeypatch):
    monkeypatch.chdir(legacy.parent.parent)
    monkeypatch.setattr(config_migration, "list_audio_devices", no_audio)
    (config_dir / "config.json").write_text(v2_text())

    assert cli.main(["config", "migrate"]) == 0
    assert json.loads((config_dir / "config.json").read_text())["version"] == 4
