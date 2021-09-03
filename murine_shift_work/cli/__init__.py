import logging
import sys

from rich import get_console

from murine_shift_work.cli.evaluate import evaluate_args
from murine_shift_work.cli.parser import parse_args


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

    console = get_console()
    console.save_text(
        "/tmp/log.rich.txt"
    )  # FIXME: why not recording any logging output ??
    console.save_html("/tmp/log.rich.html")


if __name__ == "__main__":
    run_cli()
