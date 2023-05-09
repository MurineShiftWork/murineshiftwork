import logging
import sys

from open_ephys_remote.cli.parser import parse_args


def run_cli(*args):
    """Command line interface for OpenEphys Remote with GUI version >0.6.0."""
    if not args:
        args = sys.argv[1:]

    if len(args) > 0 and not isinstance(args[0], str):
        args = args[0]

    if len(args) > 0 and str(args[0]).endswith(".py"):
        _, args = args[0], args[1:]

    if len(args) <= 1:
        args = args + ["-h"]

    args_dict = parse_args(args=args)

    if "exit_flag" in args_dict.keys():
        return

    # Call module
    args_dict["func"](**args_dict)

    logging.debug("EXITING CLI.")


if __name__ == "__main__":
    # sys.argv += [
    #     "record",
    #     "-ip",
    #     "192.168.100.19",
    #     "--prepend-text",
    #     settings["prepend_text"],
    #     "--base-text",
    #     settings["base_text"],
    #     "--append-text",
    #     settings["append_text"],
    #     "--parent-directory",
    #     settings["parent_directory"],
    # ]

    args = [
        "record",
        "-ip",
        "192.168.100.19",
        "--subject",
        "_test_oe_argv",
        "--session-extension",
        "ephys_intan",
    ]
    run_cli(args)
