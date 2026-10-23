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
        service_sub.add_parser(action, help=f"{action} the service", parents=[common]).set_defaults(handler=_not_implemented(f"service {action}"))

    sub.add_parser("doctor", help="check the setup", parents=[common]).set_defaults(handler=_not_implemented("doctor"))

    config = sub.add_parser("config", help="inspect and migrate the config", parents=[common])
    config_sub = config.add_subparsers(dest="config_command", metavar="ACTION", required=True)
    config_sub.add_parser("path", help="print the config file path", parents=[common]).set_defaults(handler=_config_path)
    config_sub.add_parser("migrate", help="migrate a 2.x config", parents=[common]).set_defaults(handler=_not_implemented("config migrate"))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_dir = getattr(args, "config_dir", None)
    if config_dir:
        paths.set_config_dir(config_dir)
    return args.handler(args)
