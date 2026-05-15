import logging
import sys

import rich

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
    # ]

    args = [
        "record",
        "-ip",
        "localhost",
        "--local-path",
        "/mnt/fastdata/data/",
        "--remote-path",
        "/mnt/fastdata/data/",
        "--subject",
        "_test_oe_argv",
        "--session-extension",
        "ephys_intan_ttl",
        # "--is-child-session-to",
        # "_test_oe_argv/_test_oe_argv__20300509_111519__testy",
    ]
    # args = [
    #     "record",
    #     "-ip",
    #     "192.168.100.230",
    #     "--local-path",
    #     "/mnt/fastdata/data/",
    #     "--remote-path",
    #     "D:\\\\neuropixel\\\\lbr\\\\",
    #     "--subject",
    #     "_test_oe_argv",
    #     "--session-extension",
    #     "ephys_pxi",
    #     # "--is-child-session-to",
    #     # "_test_oe_argv/_test_oe_argv__20300509_111519__testy",
    # ]
    run_cli(args)
