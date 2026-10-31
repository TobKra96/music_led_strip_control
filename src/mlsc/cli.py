"""Command line interface. `mlsc` alone is `mlsc run`."""
from __future__ import annotations

import argparse
import sys

from mlsc import __version__, config_migration, paths


def run_server() -> int:
    from mlsc.main import run  # ruff: ignore[import-outside-top-level] Heavy import, only needed for `run`.

    return run()


def _service(args: argparse.Namespace) -> int:
    from mlsc import service  # ruff: ignore[import-outside-top-level] Only needed for `service`.
    from mlsc.host import Host  # ruff: ignore[import-outside-top-level] Only needed for `service`.

    manager = service.ServiceManager(Host())
    try:
        if args.service_command == "status":
            code, output = manager.status()
            print(output)  # ruff: ignore[print]
            return code
        for line in getattr(manager, args.service_command)():
            print(line)  # ruff: ignore[print]
    except service.ServiceError as e:
        print(f"mlsc service {args.service_command}: {e}", file=sys.stderr)  # ruff: ignore[print]
        return 1
    return 0


def _doctor(_: argparse.Namespace) -> int:
    from mlsc import doctor  # ruff: ignore[import-outside-top-level] Pulls in the outputs and the validator, only needed for `doctor`.

    return doctor.run(paths.config_dir())


def _config_path(_: argparse.Namespace) -> int:
    print(paths.config_dir() / "config.json")  # ruff: ignore[print]
    return 0


def _config_migrate(args: argparse.Namespace) -> int:
    config_dir = paths.config_dir()
    try:
        current = config_dir / config_migration.CONFIG_FILE
        source = config_migration.find_legacy_config(args.source) if args.source or not current.is_file() else current
        if source is None:
            source = current
            if not source.is_file():
                print("mlsc config migrate: no config found. Use --from PATH for a 2.x config.", file=sys.stderr)  # ruff: ignore[print]
                return 1
        result = config_migration.migrate_file(
            source, config_dir, dry_run=args.dry_run, audio_devices=config_migration.list_audio_devices()
        )
    except config_migration.ConfigMigrationError as e:
        print(f"mlsc config migrate: {e}\nNothing was changed. {config_migration.HELP_HINT}", file=sys.stderr)  # ruff: ignore[print]
        return 1

    report = result.report
    print(f"Config version {report.from_version} -> {report.to_version} ({len(report.entries)} report entries)")  # ruff: ignore[print]
    for entry in report.entries:
        print(f"  {entry['level']}: {entry['message']} ({entry['path']})")  # ruff: ignore[print]
    if args.dry_run:
        print("Dry run: nothing was written.")  # ruff: ignore[print]
    else:
        print(f"Wrote {result.target}\nOriginal copied to {result.backup}")  # ruff: ignore[print]
    return 0


def _config_reset(_: argparse.Namespace) -> int:
    kept = config_migration.reset_config(paths.config_dir())
    print(f"Config reset to the defaults.{f' The previous config is kept as {kept}.' if kept else ''}")  # ruff: ignore[print]
    return 0


def build_parser() -> argparse.ArgumentParser:
    # Shared by every (sub)parser so the flag works before or after the subcommand. SUPPRESS keeps a subparser from resetting it.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config-dir",
        metavar="DIR",
        default=argparse.SUPPRESS,
        help=f"directory for config and data (default: platform default, or ${paths.CONFIG_DIR_ENV})",
    )

    parser = argparse.ArgumentParser(prog="mlsc", description="Music LED Strip Control", parents=[common])
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.set_defaults(handler=lambda _: run_server())
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("run", help="run the server (default)", parents=[common])

    service = sub.add_parser("service", help="manage the systemd service", parents=[common])
    service_sub = service.add_subparsers(dest="service_command", metavar="ACTION", required=True)
    for action in ("install", "uninstall", "status", "restart"):
        service_sub.add_parser(action, help=f"{action} the service", parents=[common]).set_defaults(handler=_service)

    sub.add_parser("doctor", help="check the setup", parents=[common]).set_defaults(handler=_doctor)

    config = sub.add_parser("config", help="inspect and migrate the config", parents=[common])
    config_sub = config.add_subparsers(dest="config_command", metavar="ACTION", required=True)
    config_sub.add_parser("path", help="print the config file path", parents=[common]).set_defaults(handler=_config_path)
    migrate = config_sub.add_parser("migrate", help="migrate a 2.x config", parents=[common])
    migrate.add_argument("--from", dest="source", metavar="PATH", help="legacy config file or its directory (default: ./.mlsc, then /share/.mlsc)")
    migrate.add_argument("--dry-run", action="store_true", help="show what would change without writing anything")
    migrate.set_defaults(handler=_config_migrate)
    config_sub.add_parser("reset", help="replace the config with the defaults", parents=[common]).set_defaults(handler=_config_reset)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_dir = getattr(args, "config_dir", None)
    if config_dir:
        paths.set_config_dir(config_dir)
    return args.handler(args)
