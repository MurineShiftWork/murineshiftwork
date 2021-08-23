import logging
import sys

from murine_shift_work.cli.evaluate import evaluate_args
from murine_shift_work.cli.parser import parse_args
from murine_shift_work.logic.config import setup_logging


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

    print(args)

    args_dict = parse_args(args=args)
    args_dict = evaluate_args(args_dict=args_dict)

    # Call module
    args_dict["func"](**args_dict)
    logging.debug("EXITING CLI.")


def _test_register():
    a = sys.argv + [
        "register",
        "move",
        "-s",
        "_test_register2",
        "-m",
        "-n",
        "_super_secret_alias",
        "-d",
    ]  # "-s", "some_subject", "-t", "prob"]
    run_cli(*a)


def _test_run():
    a = sys.argv + ["run", "-t", "prob", "-s", "test_run_subject", "-d"]
    run_cli(*a)


if __name__ == "__main__":
    testing = True
    if testing:
        _test_register()
    else:
        run_cli()
