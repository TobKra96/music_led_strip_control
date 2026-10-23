"""Command line interface. `mlsc` alone is `mlsc run`."""
from __future__ import annotations

import argparse
import sys

from mlsc import __version__, paths


def run_server() -> int:
    from mlsc.main import run  # ruff: ignore[import-outside-top-level] Heavy import, only needed for `run`.

    return run()


def _not_implemented(name: str):
    def handler(_: argparse.Namespace) -> int:
        print(f"mlsc {name}: not implemented yet", file=sys.stderr)  # ruff: ignore[print]
        return 1

    return handler


def _config_path(_: argparse.Namespace) -> int:
    print(paths.config_dir() / "config.json")  # ruff: ignore[print]
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mlsc", description="Music LED Strip Control")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config-dir",
        metavar="DIR",
        help=f"directory for config and data (default: platform default, or ${paths.CONFIG_DIR_ENV})",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    run = sub.add_parser("run", help="run the server (default)")
    run.set_defaults(handler=lambda _: run_server())

    service = sub.add_parser("service", help="manage the systemd service")
    service_sub = service.add_subparsers(dest="service_command", metavar="ACTION", required=True)
    for action in ("install", "uninstall", "status", "restart"):
        service_sub.add_parser(action, help=f"{action} the service").set_defaults(handler=_not_implemented(f"service {action}"))

    sub.add_parser("doctor", help="check the setup").set_defaults(handler=_not_implemented("doctor"))

    config = sub.add_parser("config", help="inspect and migrate the config")
    config_sub = config.add_subparsers(dest="config_command", metavar="ACTION", required=True)
    config_sub.add_parser("path", help="print the config file path").set_defaults(handler=_config_path)
    config_sub.add_parser("migrate", help="migrate a 2.x config").set_defaults(handler=_not_implemented("config migrate"))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.config_dir:
        paths.set_config_dir(args.config_dir)
    handler = getattr(args, "handler", None) or (lambda _: run_server())
    return handler(args)
