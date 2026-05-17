import logging
import sys

from murineshiftwork.cli.evaluate import evaluate_args
from murineshiftwork.cli.parser import parse_args
from murineshiftwork.hardware.bpod import patch_user_settings
from murineshiftwork.logic.log import patch_logging_levels


def _print_run_banner():
    from importlib.metadata import version as _v

    try:
        ver = _v("murineshiftwork")
    except Exception:
        ver = "unknown"
    print(f"msw {ver} | © Lars B. Rollik | PolyForm Internal Use 1.0.0")


def run_cli(*args):
    """Command line interface for Murine Shift Work."""
    patch_logging_levels()
    patch_user_settings()

    if not args:
        args = sys.argv[1:]

    if len(args) > 0 and not isinstance(args[0], str):
        args = args[0]

    if len(args) > 0 and str(args[0]).endswith(".py"):
        _, args = args[0], args[1:]

    if len(args) <= 1:
        args = args + ["-h"]

    args_dict = parse_args(args=args)

    # These subcommands bypass evaluate_args (no hardware/subject/task context needed)
    if args_dict.get("command") in (
        "init",
        "setup",
        "subject",
        "calibration",
        "action",
        "register",
    ):
        args_dict["func"](**args_dict)
        logging.debug("EXITING CLI.")
        return

    if args_dict.get("command") == "run":
        _print_run_banner()

    args_dict = evaluate_args(args_dict=args_dict)

    if "exit_flag" in args_dict.keys():
        return

    # Call module
    args_dict["func"](**args_dict)

    logging.debug("EXITING CLI.")


if __name__ == "__main__":
    run_cli()
