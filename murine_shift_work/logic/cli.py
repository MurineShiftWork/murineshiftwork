import logging
import os
import sys
from argparse import ArgumentDefaultsHelpFormatter
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from argparse import SUPPRESS
from pathlib import Path
from textwrap import dedent

from murine_shift_work import __version__
from murine_shift_work.logic.config import setup_logging


def register(
    cmd=None, data_path=None, subject=None, task=None, config_file_dir=None, **kwargs
):
    """

    :param cmd:
    :param data_path:
    :param subject:
    :param task:
    :param config_file_dir:
    :param kwargs:
    :return:
    """
    print("in register", kwargs)
    print(" ")


def run_task(
    data_path=None,
    subject=None,
    task=None,
    config_file_dir=None,
    config_file_rcc=None,
    serial_port=None,
    **kwargs,
):
    """
    msw run -s subject -t task
    msw run -s subject -t task -p serial_port

    :param data_path:
    :param subject:
    :param task:
    :param config_file_dir:
    :param config_file_rcc:
    :param serial_port:
    :param kwargs:
    :return:
    """
    print("in run", kwargs)
    print(" ")


def evaluate_args(arg_dict=None):
    """

    :param arg_dict:
    :return:
    """
    # TODO: add pre eval of args and config files here

    try:
        d_int = int(arg_dict["log_level"])
        arg_dict["log_int"] = d_int
        arg_dict["log_level"] = logging.getLevelName(d_int)
    except ValueError:
        pass

    return arg_dict


user_dir = Path(os.path.expanduser("~"))
default_out_path = str(user_dir / "data")


def add_args_for_general_args(parser=None):
    general_args = parser.add_argument_group("General arguments")
    general_args.add_argument(
        "-s", "--subject", type=str, default="_test_subject", help="Subject name"
    )
    general_args.add_argument(
        "-t",
        "--task",
        type=str,
        default="",
        required=True,
        help="Task name or part name",
    )
    general_args.add_argument(
        "-o",
        "--out-path",
        type=str,
        default=default_out_path,
        help="Out path for task data",
    )

    # TODO: subject, task->required, config-file-dir, config-name-rcc, config-name-subjects, config-name-tasks, serial-port

    return general_args


def add_args_for_hardware(parser=None):
    hardware_args = parser.add_argument_group("Hardware settings")
    hardware_args.add_argument(
        "-b",
        "--serial-port-bpod",
        type=str,
        default="/dev/ttyACM0",
        help="Serial port for bpod. Unix: /dev/ttyACM{no}. Windows: COM{no}.",
    )
    hardware_args.add_argument(
        "-p",
        "--serial-port-pulsepal",
        type=str,
        default="/dev/ttyACM1",
        help="Serial port for pulsepal. Unix: /dev/ttyACM{no}. Windows: COM{no}.",
    )

    return hardware_args


def add_args_for_flow_control(parser=None):
    flow_control_options = parser.add_argument_group("Development options.")
    flow_control_options.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        type=str,
        default="INFO",
    )
    return flow_control_options


class ArgparseFormatter(ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter):
    pass


def make_subparser_register(sub_parsers):
    description = "Register subjects"
    examples = dedent(
        """Examples:

    msw register subject [optional: task]

    msw register add _test_subject
    msw register add _test_subject probabilistic_switching
    msw register add _test_subject -t/--task probabilistic_switching
    msw register remove _test_subject
    msw register remove _test_subject --task probabilistic_switching

    """
    )
    parser_for_register = sub_parsers.add_parser(
        name="register",
        description=description,
        help=description,
        epilog=examples,
        formatter_class=ArgparseFormatter,
    )

    parser_for_register.add_argument("cmd")

    # parser_register_add = parser_for_register.add_parser(name="add", formatter = ArgparseFormatter)
    # add_args_for_general_args(parser_register_add)
    # add_args_for_flow_control(parser_register_add)
    # parser_register_add.set_defaults(func=register_add)
    #
    # parser_register_remove = parser_for_register.add_parser(name="remove", formatter=ArgparseFormatter)
    # add_args_for_general_args(parser_register_remove)
    # add_args_for_flow_control(parser_register_remove)
    # parser_register_remove.set_defaults(func=register_remove)

    # parser_for_register.add_argument("add")
    # parser_for_register.add_argument("remove")
    #
    add_args_for_general_args(parser_for_register)
    add_args_for_flow_control(parser_for_register)
    parser_for_register.set_defaults(func=register)


def make_subparser_run(sub_parsers):
    description = "Run tasks"
    examples = dedent(
        """Examples:

    msw run -t task_name -s subject_name
    msw run -t task_name -s subject_name -b serial_port_bpod

    """
    )
    parser_for_run = sub_parsers.add_parser(
        name="run",
        description=description,
        help=description,
        epilog=examples,
        formatter_class=ArgparseFormatter,
    )
    add_args_for_general_args(parser_for_run)
    add_args_for_hardware(parser_for_run)
    add_args_for_flow_control(parser_for_run)
    parser_for_run.set_defaults(func=run_task)


def parse_args(args=None):
    main_parser = ArgumentParser(
        prog="msw",
        description="Behavior acquisition for murine tasks. "
        "Options for video acquisition with RPi Camera Colony and stimulation with PulsePal.",
        epilog="THE END",
        formatter_class=ArgparseFormatter,
    )
    main_parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"Murine Shift Work: {__version__}",
        help="Show the version number and exit.",
    )
    sub_parsers = main_parser.add_subparsers(metavar="command", dest="cmd")
    sub_parsers.required = True
    make_subparser_register(sub_parsers)
    make_subparser_run(sub_parsers)

    parsed_args = main_parser.parse_args(args=args)
    return parsed_args.__dict__


def run_msw_cli(*args):  # TODO: link in setup.py
    """Command line interface for Murine Shift Work."""
    # Args from call, otherwise get sys
    if not args:
        args = sys.argv

    if len(args) < 1:
        raise ValueError("Missing arguments")

    if len(args) > 0 and not isinstance(args[0], str):
        args = args[0]

    if len(args) > 0 and str(args[0]).endswith(".py"):
        _, args = args[0], args[1:]

    if len(args) <= 1:
        args = args + ("-h",)

    parsed_args = parse_args(args=args)

    parsed_args = evaluate_args(arg_dict=parsed_args)
    setup_logging(level=parsed_args["log_level"])

    # Call module
    parsed_args["func"](**parsed_args)


if __name__ == "__main__":
    a = sys.argv + [
        "register",
        "add",
        "-s",
        "test_register",
        "-t",
        "video",
    ]  # "-s", "some_subject", "-t", "prob"]
    run_msw_cli(*a)

    a = sys.argv + ["run", "-t", "sth"]
    run_msw_cli(*a)
    print("main")
