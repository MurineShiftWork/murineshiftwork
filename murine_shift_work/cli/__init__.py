import logging
import sys

from murine_shift_work.cli.evaluate import evaluate_args
from murine_shift_work.cli.parser import parse_args
from murine_shift_work.logic.pybpod_helpers import patch_logging_levels


def run_cli(*args):
    """Command line interface for Murine Shift Work."""
    if not args:
        args = sys.argv[1:]

    if len(args) > 0 and not isinstance(args[0], str):
        args = args[0]

    if len(args) > 0 and str(args[0]).endswith(".py"):
        _, args = args[0], args[1:]

    if len(args) <= 1:
        args = args + ["-h"]

    args_dict = parse_args(args=args)
    args_dict = evaluate_args(args_dict=args_dict)

    if "exit_flag" in args_dict.keys():
        return

    # Call module
    args_dict["func"](**args_dict)
    logging.debug("EXITING CLI.")


if __name__ == "__main__":
    patch_logging_levels()
    run_cli()
