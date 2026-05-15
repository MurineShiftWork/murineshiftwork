import sys

from oe_remote._version import __version__
from oe_remote.cli.parser import parse_args


def run_cli(args=None):
    """Entry point for the ``oe-remote`` CLI."""
    if args is None:
        args = sys.argv[1:]

    # Allow passing a list directly (e.g. from tests or __main__)
    if args and not isinstance(args[0], str):
        args = list(args[0])

    parsed = parse_args(args if args else ["-h"])

    if "func" not in parsed:
        return

    func = parsed.pop("func")
    func(**parsed)
